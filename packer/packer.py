#!/usr/bin/env python3

# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# ***** END GPL LICENCE BLOCK *****

import blendfile_path_walker

TIMEIT = True


def pack(blendfile_src, blendfile_dst, mode='FILE',
         deps_remap=None, paths_remap=None):
    """
    :param deps_remap: Store path deps_remap info as follows.
       {"file.blend": {"path_new": "path_old", ...}, ...}

    :type deps_remap: dict or None
    """

    # Internal details:
    # - we copy to a temp path before operating on the blend file
    #   so we can modify in-place.
    # - temp files are only created once, (if we never touched them before),
    #   this way, for linked libraries - a single blend file may be used
    #   multiple times, each access will apply new edits ontop of the old ones.
    # - we track which libs we have touched (using 'lib_visit' arg),
    #   this means that the same libs wont be touched many times to modify the same data
    #   also prevents cyclic loops from crashing.

    import os
    import shutil

    path_temp_files = set()
    path_copy_files = set()

    SUBDIR = b'data'
    TEMP_SUFFIX = b'@'

    if TIMEIT:
        import time
        t = time.time()

    def temp_remap_cb(filepath, level):
        """
        Create temp files in the destination path.
        """
        filepath = blendfile_path_walker.utils.compatpath(filepath)

        if level == 0:
            filepath_tmp = os.path.join(base_dir_dst, os.path.basename(filepath)) + TEMP_SUFFIX
        else:
            filepath_tmp = os.path.join(base_dir_dst, SUBDIR, os.path.basename(filepath)) + TEMP_SUFFIX

        filepath_tmp = os.path.normpath(filepath_tmp)

        # only overwrite once (so we can write into a path already containing files)
        if filepath_tmp not in path_temp_files:
            shutil.copy(filepath, filepath_tmp)
            path_temp_files.add(filepath_tmp)
        return filepath_tmp

    # base_dir_src = os.path.dirname(blendfile_src)
    base_dir_dst = os.path.dirname(blendfile_dst)

    base_dir_dst_subdir = os.path.join(base_dir_dst, SUBDIR)
    if not os.path.exists(base_dir_dst_subdir):
        os.makedirs(base_dir_dst_subdir)

    lib_visit = {}

    for fp, (rootdir, fp_blend_basename) in blendfile_path_walker.FilePath.visit_from_blend(
            blendfile_src,
            readonly=False,
            temp_remap_cb=temp_remap_cb,
            recursive=True,
            lib_visit=lib_visit,
            ):

        # assume the path might be relative
        path_src_orig = fp.filepath
        path_rel = blendfile_path_walker.utils.compatpath(path_src_orig)
        path_base = path_rel.split(os.sep.encode('ascii'))[-1]
        path_src = blendfile_path_walker.utils.abspath(path_rel, fp.basedir)

        # rename in the blend
        path_dst = os.path.join(base_dir_dst_subdir, path_base)

        if fp.level == 0:
            path_dst_final = b"//" + os.path.join(SUBDIR, path_base)
        else:
            path_dst_final = b'//' + path_base

        fp.filepath = path_dst_final

        # add to copy-list
        # never copy libs (handled separately)
        if not isinstance(fp, blendfile_path_walker.FPElem_block_path) or fp.userdata[0].code != b'LI':
            path_copy_files.add((path_src, path_dst))

        if deps_remap is not None:
            # this needs to become JSON later... ugh, need to use strings
            deps_remap.setdefault(
                    fp_blend_basename.decode('utf-8'),
                    {})[path_dst_final.decode('utf-8')] = path_src_orig.decode('utf-8')

    del lib_visit

    if TIMEIT:
        print("  Time: %.4f\n" % (time.time() - t))

    # handle deps_remap and file renaming
    if deps_remap is not None:
        blendfile_src_basename = os.path.basename(blendfile_src).decode('utf-8')
        blendfile_dst_basename = os.path.basename(blendfile_dst).decode('utf-8')

        if blendfile_src_basename != blendfile_dst_basename:
            deps_remap[blendfile_dst_basename] = deps_remap[blendfile_src_basename]
            del deps_remap[blendfile_src_basename]
        del blendfile_src_basename, blendfile_dst_basename

    # store path mapping {dst: src}
    if paths_remap is not None:
        for src, dst in path_copy_files:
            # TODO. relative to project-basepath
            paths_remap[os.path.relpath(dst, base_dir_dst).decode('utf-8')] = src.decode('utf-8')
    # paths_remap[os.path.relpath(dst, base_dir_dst)] = blendfile_src

    # --------------------
    # Handle File Copy/Zip

    if mode == 'FILE':
        blendfile_dst_tmp = temp_remap_cb(blendfile_src, 0)

        shutil.move(blendfile_dst_tmp, blendfile_dst)
        path_temp_files.remove(blendfile_dst_tmp)

        # strip TEMP_SUFFIX
        for fn in path_temp_files:
            shutil.copyfile(fn, fn[:-1])

        for src, dst in path_copy_files:
            assert(b'.blend' not in dst)

            if not os.path.exists(src):
                print("  Source missing! %r" % src)
            else:
                print("  Copying %r -> %r" % (src, dst))
                shutil.copy(src, dst)


        print("  Written:", blendfile_dst)

    elif mode == 'ZIP':
        import zipfile
        with zipfile.ZipFile(blendfile_dst.decode('utf-8'), 'w', zipfile.ZIP_DEFLATED) as zip:
            for fn in path_temp_files:
                print("  Copying %r -> <zip>" % fn)
                zip.write(fn.decode('utf-8'),
                          arcname=os.path.relpath(fn[:-1], base_dir_dst).decode('utf-8'))
                os.remove(fn)

            shutil.rmtree(base_dir_dst_subdir)

            for src, dst in path_copy_files:
                assert(b'.blend' not in dst)

                if not os.path.exists(src):
                    print("  Source missing! %r" % src)
                else:
                    print("  Copying %r -> <zip>" % src)
                    zip.write(src.decode('utf-8'),
                              arcname=os.path.relpath(dst, base_dir_dst).decode('utf-8'))

        print("  Written:", blendfile_dst)
    else:
        raise Exception("%s not a known mode" % mode)


def create_argparse():
    import os
    import argparse

    usage_text = (
        "Run this script to extract blend-files(s) to a destination path:" +
        os.path.basename(__file__) +
        "--input=FILE --output=FILE [options]")

    parser = argparse.ArgumentParser(description=usage_text)

    # for main_render() only, but validate args.
    parser.add_argument(
            "-i", "--input", dest="path_src", metavar='FILE', required=True,
            help="Input path(s) or a wildcard to glob many files")
    parser.add_argument(
            "-o", "--output", dest="path_dst", metavar='DIR', required=True,
            help="Output file or a directory when multiple inputs are passed")
    parser.add_argument(
            "-m", "--mode", dest="mode", metavar='MODE', required=False,
            choices=('FILE', 'ZIP'), default='FILE',
            help="Output file or a directory when multiple inputs are passed")
    parser.add_argument(
            "-r", "--deps_remap", dest="deps_remap", metavar='FILE',
            help="Write out the path mapping to a JSON file")
    parser.add_argument(
            "-s", "--paths_remap", dest="paths_remap", metavar='FILE',
            help="Write out the original paths to a JSON file")

    return parser


def main():
    import sys

    parser = create_argparse()
    args = parser.parse_args(sys.argv[1:])

    encoding = sys.getfilesystemencoding()

    deps_remap = {} if args.deps_remap else None
    paths_remap = {} if args.paths_remap else None

    pack(args.path_src.encode(encoding),
         args.path_dst.encode(encoding),
         args.mode,
         deps_remap,
         paths_remap,
         )

    if deps_remap is not None:
        import json

        with open(args.deps_remap, 'w', encoding='utf-8') as f:
            json.dump(
                    deps_remap, f, ensure_ascii=False,
                    # optional (pretty)
                    sort_keys=True, indent=4, separators=(',', ': '),
                    )

    if paths_remap is not None:
        import json

        with open(args.paths_remap, 'w', encoding='utf-8') as f:
            json.dump(
                    paths_remap, f, ensure_ascii=False,
                    # optional (pretty)
                    sort_keys=True, indent=4, separators=(',', ': '),
                    )

if __name__ == "__main__":
    main()
