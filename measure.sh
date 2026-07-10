#!/usr/bin/env bash
set -euo pipefail

if [ -d sensor_output ]; then
  rm -rf sensor_output
fi

mkdir sensor_output
docker run --rm -d --name hwpc-sensor --net=host --privileged --pid=host -v /sys:/sys -v /var/lib/docker/containers:/var/lib/docker/containers:ro -v $(pwd)/sensor_output:/tmp/sensor_output -v $(pwd):/srv -v $(pwd)/config_file.json:/config_file.json powerapi/hwpc-sensor --config-file /config_file.json
