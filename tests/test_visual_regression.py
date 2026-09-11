"""Execute the optional macOS helper with real PNGs; no App or external package needed."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / '.agents/skills/ios-workflow/scripts/visual_snapshot.swift'


def write_png(path, *, changed=False, width=4, height=3):
    """Create a tiny opaque PNG fixture with an optional single changed pixel."""
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend((240, 20, 40, 255) if changed and (x, y) == (2, 1) else (20, 80, 160, 255))
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 6, 0, 0, 0))
    path.write_bytes(data + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


@unittest.skipUnless(sys.platform == 'darwin' and shutil.which('swiftc'), 'Native PNG helper requires macOS/Swift')
class VisualRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compiler_dir = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.compiler_dir.cleanup)
        cls.binary = Path(cls.compiler_dir.name) / 'visual-snapshot'
        result = subprocess.run(['swiftc', str(HELPER), '-o', str(cls.binary)], capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise RuntimeError(result.stderr)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.image = self.root / 'current.png'
        write_png(self.image)
        self.context_path = self.root / 'context.json'
        self.context = {'xcode': 'fixture-only', 'simulator_runtime': 'fixture-only', 'device_model': 'fixture-only',
                        'locale': 'en_US', 'interface_style': 'light', 'content_size_category': 'large',
                        'orientation': 'portrait', 'scenario': 'synthetic-pixel-comparator-regression',
                        'viewport_width_points': 4, 'viewport_height_points': 3, 'display_scale': 1}
        self.context_path.write_text(json.dumps(self.context))
        self.baseline = self.root / 'baseline'

    def execute(self, action, *extra):
        return subprocess.run([str(self.binary), action, '--image', str(self.image), '--context', str(self.context_path),
                               '--baseline', str(self.baseline), *map(str, extra)],
                              text=True, capture_output=True, timeout=30)

    def record(self):
        result = self.execute('record', '--reviewed-by', 'synthetic fixture test',
                              '--review-reference', 'automated comparator fixture; not product acceptance')
        self.assertEqual(0, result.returncode, result.stderr)

    def test_identical_real_png_passes_with_exact_pixel_report(self):
        self.record()
        output = self.root / 'comparison'
        result = self.execute('compare', '--output', output)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads((output / 'report.json').read_text())
        self.assertEqual('passed', report['result'])
        self.assertEqual(0, report['changed_pixels'])
        self.assertEqual(12, report['total_pixels'])

    def test_single_changed_pixel_fails_produces_diff_and_preserves_baseline(self):
        self.record()
        original = (self.baseline / 'image.png').read_bytes()
        manifest = (self.baseline / 'manifest.json').read_bytes()
        write_png(self.image, changed=True)
        output = self.root / 'comparison'
        result = self.execute('compare', '--output', output)
        self.assertEqual(1, result.returncode, result.stderr)
        report = json.loads((output / 'report.json').read_text())
        self.assertEqual('failed', report['result'])
        self.assertEqual(1, report['changed_pixels'])
        self.assertTrue((output / 'diff.png').read_bytes().startswith(b'\x89PNG'))
        self.assertEqual(original, (self.baseline / 'image.png').read_bytes())
        self.assertEqual(manifest, (self.baseline / 'manifest.json').read_bytes())

    def test_environment_drift_blocks_even_when_pixels_match(self):
        self.record()
        self.context['xcode'] = 'different-fixture-toolchain'
        self.context_path.write_text(json.dumps(self.context))
        output = self.root / 'comparison'
        result = self.execute('compare', '--output', output)
        self.assertEqual(2, result.returncode)
        self.assertEqual('blocked', json.loads((output / 'report.json').read_text())['result'])

    def test_missing_baseline_never_auto_records_and_review_declaration_is_required(self):
        result = self.execute('record')
        self.assertEqual(2, result.returncode)
        self.assertFalse(self.baseline.exists())
        result = self.execute('compare', '--output', self.root / 'comparison')
        self.assertEqual(2, result.returncode)
        self.assertFalse(self.baseline.exists())

    def test_existing_baseline_or_output_cannot_be_overwritten(self):
        self.record()
        manifest = (self.baseline / 'manifest.json').read_bytes()
        result = self.execute('record', '--reviewed-by', 'different reviewer', '--review-reference', 'different reference')
        self.assertEqual(2, result.returncode)
        self.assertEqual(manifest, (self.baseline / 'manifest.json').read_bytes())
        output = self.root / 'comparison'
        self.assertEqual(0, self.execute('compare', '--output', output).returncode)
        report = (output / 'report.json').read_bytes()
        self.assertEqual(2, self.execute('compare', '--output', output).returncode)
        self.assertEqual(report, (output / 'report.json').read_bytes())

    def test_changed_baseline_or_invalid_capture_dimensions_cannot_pass(self):
        self.record()
        write_png(self.baseline / 'image.png', changed=True)
        self.assertEqual(2, self.execute('compare', '--output', self.root / 'comparison').returncode)
        self.context['display_scale'] = 2
        self.context_path.write_text(json.dumps(self.context))
        self.assertEqual(2, self.execute('compare', '--output', self.root / 'other').returncode)

    def test_example_placeholders_cannot_be_used_as_capture_facts(self):
        self.context['xcode'] = 'REPLACE_WITH_ACTUAL_VERSION_AND_BUILD'
        self.context_path.write_text(json.dumps(self.context))
        result = self.execute('record', '--reviewed-by', 'fixture', '--review-reference', 'fixture')
        self.assertEqual(2, result.returncode)
        self.assertFalse(self.baseline.exists())

    def test_unknown_environment_values_block_record_and_compare_after_normalization(self):
        placeholders = ['unknown', ' INComplete ', 'not_run', ' NOT \n RUN ', 'N/A', ' TBD\t',
                        ' 未知 ', '待补充', '  replace_WITH_ACTUAL_VERSION  ']
        # Even a legacy baseline carrying the same unknown value must not turn green.
        self.record()
        original_manifest = json.loads((self.baseline / 'manifest.json').read_text())
        original_baseline = self.baseline
        for index, value in enumerate(placeholders):
            with self.subTest(value=value):
                self.context['xcode'] = value
                self.context_path.write_text(json.dumps(self.context))
                self.baseline = self.root / f'new-baseline-{index}'
                result = self.execute('record', '--reviewed-by', 'fixture', '--review-reference', 'fixture')
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertFalse(self.baseline.exists())
                self.baseline = original_baseline
                manifest = dict(original_manifest, context=dict(self.context))
                (self.baseline / 'manifest.json').write_text(json.dumps(manifest))
                result = self.execute('compare', '--output', self.root / f'comparison-{index}')
                self.assertEqual(2, result.returncode, result.stderr)

    def test_boolean_manifest_fields_cannot_masquerade_as_integer_one(self):
        # JSON true bridges to Swift Int(1); 1x1 fixtures exercise each affected field.
        write_png(self.image, width=1, height=1)
        self.context.update(viewport_width_points=1, viewport_height_points=1)
        self.context_path.write_text(json.dumps(self.context))
        self.record()
        original_manifest = json.loads((self.baseline / 'manifest.json').read_text())
        for field in ('schema_version', 'width', 'height'):
            with self.subTest(field=field):
                manifest = dict(original_manifest, **{field: True})
                (self.baseline / 'manifest.json').write_text(json.dumps(manifest))
                output = self.root / f'comparison-{field}'
                result = self.execute('compare', '--output', output)
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertEqual('blocked', json.loads((output / 'report.json').read_text())['result'])


if __name__ == '__main__':
    unittest.main()
