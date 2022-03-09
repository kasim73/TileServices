#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: ${0} <build_number>"
    exit 1
fi

build_number=${1}
plugin_id="com_github_kasim73_tile_services"
root_dir="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source_dir_name=com_github_kasim73_tile_services
source_dir=${root_dir}/com_github_kasim73_tile_services
build_dir=${root_dir}/build

rm -rf ${build_dir}
mkdir -p ${build_dir}
cp -r ${source_dir} ${build_dir}/${plugin_id}

work_dir=${build_dir}/${plugin_id}

cd ${work_dir}
find . | grep -E "(\.git|__pycache__|\.pyc|\.DS_Store|\.dSYM$|\.pyo$|\.ts|\.pro)" | xargs rm -rf
sed -i -e "/^version=.*/a build_number=${build_number}" manifest.ini
cd ${build_dir}
zip -r ${plugin_id}-${build_number}.axp ${plugin_id}
