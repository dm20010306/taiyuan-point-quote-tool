#!/bin/zsh
script_dir="${0:A:h}"
export POINT_QUOTE_SOURCE_DIR="$script_dir"
exec /bin/zsh "$script_dir/macos-launcher/run-macos.zsh.txt"
