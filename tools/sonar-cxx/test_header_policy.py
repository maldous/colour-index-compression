"""Header policy must distinguish ownership and exact license identifiers."""
import json
import re
import unittest
from header_policy import POLICY, header_matches, licensed_paths


class HeaderPolicyTests(unittest.TestCase):
    def test_exact_comment_forms(self):
        for identifier in ('MIT', 'GPL-2.0-only'):
            for line in (f'// SPDX-License-Identifier: {identifier}',
                         f'/* SPDX-License-Identifier: {identifier} */'):
                self.assertTrue(header_matches(line, identifier))

    def test_reject_wrong_or_embedded_identifiers(self):
        for line in ('', '// SPDX-License-Identifier: MIT-other',
                     '// SPDX-License-Identifier: GPL-2.0-only',
                     'const char *s = "SPDX-License-Identifier: MIT";',
                     '// SPDX-License-Identifier: MIT OR GPL-2.0-only'):
            self.assertFalse(header_matches(line, 'MIT'))

    def test_scope_rejects_wrong_classification_and_vendor(self):
        paths = ['rust/cix-native/adapters/squashfs/kernel/file.c',
                 'rust/cix-native/adapters/vendor/file.c', '../file.c']
        for path in paths:
            with self.assertRaises(ValueError):
                licensed_paths({'userspace_mit': [path], 'kernel_gpl_2_only': []})
        with self.assertRaises(ValueError):
            licensed_paths({'userspace_mit': [], 'kernel_gpl_2_only': [
                'rust/cix-native/bindings/node/src/cix_node.c']})

    def test_frozen_scope_and_plugin_regex(self):
        policy = json.loads(POLICY.read_text())
        self.assertEqual(len(licensed_paths(policy)), 55)
        expression = re.compile(policy['file_header_regex'])
        for identifier in ('MIT', 'GPL-2.0-only'):
            self.assertIsNotNone(expression.fullmatch(f'// SPDX-License-Identifier: {identifier}'))
            self.assertIsNotNone(expression.fullmatch(f'/* SPDX-License-Identifier: {identifier} */'))
        self.assertIsNone(expression.fullmatch('// SPDX-License-Identifier: MIT-other'))


if __name__ == '__main__':
    unittest.main()
