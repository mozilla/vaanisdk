# The Vaani Speech SDK

| Component       | Status                                                                                                                           |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------|
| SmartHome       | [![Build Status](https://travis-ci.org/mozilla/smarthome.svg?branch=master)](https://travis-ci.org/mozilla/smarthome)            |
| OpenHAB core    | [![Build Status](https://travis-ci.org/mozilla/openhab-core.svg?branch=master)](https://travis-ci.org/mozilla/openhab-core)      |
| OpenHAB         | [![Build Status](https://travis-ci.org/mozilla/openhab.svg?branch=master)](https://travis-ci.org/mozilla/openhab)                |
| OpenHAB2 addons | [![Build Status](https://travis-ci.org/mozilla/openhab2-addons.svg?branch=master)](https://travis-ci.org/mozilla/openhab2-addons)|
| OpenHAB distro  | [![Build Status](https://travis-ci.org/mozilla/openhab-distro.svg?branch=master)](https://travis-ci.org/mozilla/openhab-distro)  |


### Prerequisites
 - git
 - Python 2.7+
 - Oracle JDK 7 or 8 or OpenJDK
 - Swig and its dependencies
 - C build essentials: gcc, libtool, bison etc.

### Build

To build Vaani, you just need to clone it and use the mach tool:

``` sh
git clone https://github.com/mozilla/vaanisdk
cd vaanisdk
./mach build all
```

```./mach help``` will give you further information regarding its possibilities.
