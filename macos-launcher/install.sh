#!/bin/zsh
set -e

launcher_dir="${0:A:h}"
build_root="$(mktemp -d)"
app_name="态元智控图纸报价工具.app"
app_path="${build_root}/${app_name}"
install_path="${HOME}/Applications/${app_name}"

cleanup() {
  rm -rf "$build_root"
}
trap cleanup EXIT

mkdir -p "$app_path/Contents/MacOS" "${HOME}/Applications"
cp "$launcher_dir/Info.plist" "$app_path/Contents/Info.plist"
clang -O2 -Wall -Wextra "$launcher_dir/launcher.c" -o "$app_path/Contents/MacOS/launcher"
codesign --force --deep --sign - "$app_path"
ditto "$app_path" "$install_path"
codesign --force --deep --sign - "$install_path"
codesign --verify --deep --strict "$install_path"

echo "已安装：${install_path}"
open "$install_path"
