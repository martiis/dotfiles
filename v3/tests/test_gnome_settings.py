import ast
import configparser
from pathlib import Path
import unittest

try:
    from gi.repository import Gio, GLib
except ImportError:
    Gio = GLib = None

SETTINGS = Path(__file__).resolve().parents[1] / "gnome" / "settings.ini"


class GnomeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.config = configparser.ConfigParser(interpolation=None)
        self.config.read(SETTINGS)

    def test_only_selected_sections_are_exported(self):
        expected = {
            "org/gnome/desktop/interface", "org/gnome/desktop/wm/preferences",
            "org/gnome/desktop/default-applications/terminal",
            "org/gnome/desktop/wm/keybindings", "org/gnome/mutter",
            "org/gnome/mutter/keybindings", "org/gnome/desktop/input-sources",
            "org/gnome/desktop/peripherals/touchpad",
            "org/gnome/settings-daemon/plugins/media-keys",
            "org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0",
            "org/gnome/shell", "org/gnome/shell/keybindings",
        }
        self.assertEqual(set(self.config.sections()), expected)

    def test_default_terminal_and_shortcut_use_alacritty(self):
        terminal = self.config["org/gnome/desktop/default-applications/terminal"]
        self.assertEqual(ast.literal_eval(terminal["exec"]), "alacritty")
        self.assertEqual(ast.literal_eval(terminal["exec-arg"]), "-e")
        shortcut = self.config[
            "org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/custom0"
        ]
        self.assertEqual(ast.literal_eval(shortcut["command"]), "/usr/bin/alacritty")
        self.assertEqual(ast.literal_eval(shortcut["binding"]), "<Super>Return")

    def test_workspace_accelerators_have_no_application_binding_conflicts(self):
        application_bindings = self.config["org/gnome/shell/keybindings"]
        self.assertEqual(
            dict(application_bindings),
            {f"switch-to-application-{number}": "@as []" for number in range(1, 5)},
        )
        application_accelerators = {
            accelerator
            for value in application_bindings.values()
            for accelerator in ast.literal_eval(value.removeprefix("@as "))
        }
        workspace_bindings = self.config["org/gnome/desktop/wm/keybindings"]
        for number in range(1, 5):
            with self.subTest(workspace=number):
                accelerators = ast.literal_eval(workspace_bindings[f"switch-to-workspace-{number}"])
                self.assertEqual(accelerators, [f"<Super>{number}"])
                self.assertTrue(application_accelerators.isdisjoint(accelerators))

    @unittest.skipIf(Gio is None, "Install python-gobject for GNOME schema validation")
    def test_all_values_match_installed_schemas_without_writing_settings(self):
        source = Gio.SettingsSchemaSource.get_default()
        for section in self.config.sections():
            schema_id = section.replace("/", ".")
            if "/custom-keybindings/" in section:
                schema_id = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
            schema = source.lookup(schema_id, True)
            self.assertIsNotNone(schema, schema_id)
            for key, value in self.config.items(section):
                with self.subTest(section=section, key=key):
                    self.assertTrue(schema.has_key(key))
                    schema_key = schema.get_key(key)
                    variant = GLib.Variant.parse(schema_key.get_value_type(), value, None, None)
                    self.assertTrue(schema_key.range_check(variant))


if __name__ == "__main__":
    unittest.main()
