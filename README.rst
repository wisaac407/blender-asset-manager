
BAM (Blender Asset Manager)
===========================

Script to manage assets with Blender.


Bundling with Blender
---------------------

Blender is bundled with a version of BAM. To update this version, first build
a new `wheel <http://pythonwheels.com/>`_ file::

    python3 setup.py bdist_wheel

Then copy this wheel to Blender::

    cp dist/blender_bam-*.whl /path/to/blender/release/scripts/addons/io_blend_utils/

Remove old wheels that are still in /path/to/blender/release/scripts/addons/io_blend_utils/
before committing.


Running bam-pack from the wheel
-------------------------------

This is the way that Blender runs bam-pack::

    PYTHONPATH=./path/to/blender_bam-*.whl python3 -m bam.pack


Bumping versions
----------------

When bumping the version to something new, make sure you update the following files:

- setup.py
- bam/__init__.py
- doc/source/conf.py
