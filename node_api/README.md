<!--
# Copyright 2023-2024 Jetperch LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
-->

# Node.js Node-API bindings for Joulescope Driver

Welcome to the Joulescope™ Driver project.
[Joulescope](https://www.joulescope.com) is an affordable, precision DC energy
analyzer that enables you to build better products.

This node.js package contains the Javascript bindings for the Joulescope driver.
See the [source code](https://github.com/jetperch/joulescope_driver)
and the main [README](https://github.com/jetperch/joulescope_driver/README.md).

See the "example" subdirectory for examples of how to use this package.


# Building

Install node.js and npm.  See [instructions](https://nodejs.github.io/node-addon-examples/getting-started/tools).

```sh
npm install
npm test
```

The driver can be included into a nodejs project. To prepare the driver for it, run the following command

```sh
npm install
npm prebuild
```

This command creates a *.node file that the node project first searches for when adding the driver. This prevent the project from rebuilding the entire driver again when adding.

## References

* https://nodejs.github.io/node-addon-examples/
* https://github.com/nodejs/node-addon-examples
* https://nodejs.org/api/n-api.html
