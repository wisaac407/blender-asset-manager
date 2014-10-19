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

VERBOSE = True
TIMEIT = True

if VERBOSE:
    _A = open("/tmp/a.log", 'w')
    class log_deps:
        @staticmethod
        def info(msg):
            _A.write(msg)
            _A.write("\n")

    def set_as_str(s):
        if s is None:
            return "None"
        else:
             return (", ".join(sorted(i.decode('ascii') for i in sorted(s))))

class FilePath:
    """
    Tiny filepath class to hide blendfile.
    """
    __slots__ = (
        "block",
        "path",
        # path may be relative to basepath
        "basedir",
        # library link level
        "level",
        )

    def __init__(self, block, path, basedir, level):
        self.block = block
        self.path = path
        self.basedir = basedir
        self.level = level

    # --------
    # filepath
    #
    @property
    def filepath(self):
        return self.block[self.path]

    @filepath.setter
    def filepath(self, filepath):
        self.block[self.path] = filepath

    # ------------------------------------------------------------------------
    # Main function to visit paths
    @staticmethod
    def visit_from_blend(
            filepath,

            # never modify the blend
            readonly=True,
            # callback that creates a temp file and returns its path.
            temp_remap_cb=None,

            # recursive options
            recursive=False,
            # list of ID block names we want to load, or None to load all
            block_codes=None,
            # root when we're loading libs indirectly
            rootdir=None,
            level=0,
            # dict of id's used so we don't follow these links again
            # prevents cyclic references too!
            # {lib_path: set([block id's ...])}
            lib_visit=None,
            ):
        # print(level, block_codes)
        import os

        if VERBOSE:
            indent_str = "  " * level
            print(indent_str + "Opening:", filepath)
            # print(indent_str + "... blocks:", block_codes)


            log_deps.info("~")
            log_deps.info("%s%s" % (indent_str, filepath.decode('utf-8')))
            log_deps.info("%s%s" % (indent_str, set_as_str(block_codes)))


        basedir = os.path.dirname(os.path.abspath(filepath))
        if rootdir is None:
            rootdir = basedir

        if recursive and (level > 0) and (block_codes is not None):
            # prevent from expanding the
            # same datablock more then once
            expand_codes = set()
            # {lib_id: {block_ids... }}
            expand_codes_idlib = {}

            # only for this block
            def _expand_codes_add_test(block, code):
                # return True, if the ID should be searched further
                #
                # we could investigate a better way...
                # Not to be accessing ID blocks at this point. but its harmless
                if code == b'ID':
                    if recursive:
                        expand_codes_idlib.setdefault(block[b'lib'], set()).add(block[b'name'])
                    return False
                else:
                    len_prev = len(expand_codes)
                    expand_codes.add(block[b'id.name'])
                    return (len_prev != len(expand_codes))

            def block_expand(block, code):
                if _expand_codes_add_test(block, code):
                    yield block

                    fn = ExpandID.expand_funcs.get(code)
                    if fn is not None:
                        for sub_block in fn(block):
                            if sub_block is not None:
                                yield from block_expand(sub_block, sub_block.code)
                else:
                    yield block
        else:
            expand_codes = None

            # set below
            expand_codes_idlib = None

            def block_expand(block, code):
                yield block

        if block_codes is None:
            def iter_blocks_id(code):
                return blend.find_blocks_from_code(code)
        else:
            def iter_blocks_id(code):
                for block in blend.find_blocks_from_code(code):
                    if block[b'id.name'] in block_codes:
                        yield from block_expand(block, code)

        if temp_remap_cb is not None:
            filepath_tmp = temp_remap_cb(filepath, level)
        else:
            filepath_tmp = filepath

        import blendfile
        blend = blendfile.open_blend(filepath_tmp, "rb" if readonly else "r+b")

        for code in blend.code_index.keys():
            # handle library blocks as special case
            if ((len(code) != 2) or
                (code in {
                    # libraries handled below
                    b'LI',
                    b'ID',
                    # unneeded
                    b'WM',
                    b'SN',  # bScreen
                    })):

                continue

            # if VERBOSE:
            #     print("  Scanning", code)

            for block in iter_blocks_id(code):
                yield from FilePath.from_block(block, basedir, rootdir, level)

        # print("A:", expand_codes)
        # print("B:", block_codes)
        if VERBOSE:
            log_deps.info("%s%s" % (indent_str, set_as_str(expand_codes)))

        if recursive:

            if expand_codes_idlib is None:
                expand_codes_idlib = {}
                for block in blend.find_blocks_from_code(b'ID'):
                    expand_codes_idlib.setdefault(block[b'lib'], set()).add(block[b'name'])

            # look into libraries
            lib_all = []

            for lib_id, lib_block_codes in sorted(expand_codes_idlib.items()):
                lib = blend.find_block_from_offset(lib_id)
                lib_path = lib[b'name']

                # get all data needed to read the blend files here (it will be freed!)
                # lib is an address at the moment, we only use as a way to group

                lib_all.append((lib_path, lib_block_codes))
                # import IPython; IPython.embed()

        # do this after, incase we mangle names above
        for block in iter_blocks_id(b'LI'):
            yield from FilePath.from_block(block, basedir, rootdir, level)

        blend.close()

        # ----------------
        # Handle Recursive
        if recursive:
            # now we've closed the file, loop on other files

            # note, sorting - isn't needed, it just gives predictable load-order.
            for lib_path, lib_block_codes in lib_all:
                lib_path_abs = os.path.normpath(utils.compatpath(utils.abspath(lib_path, basedir)))

                # if we visited this before,
                # check we don't follow the same links more than once
                lib_block_codes_existing = lib_visit.setdefault(lib_path_abs, set())
                lib_block_codes -= lib_block_codes_existing
                # don't touch them again
                lib_block_codes_existing.update(lib_block_codes)

                # print("looking for", lib_block_codes)

                # import IPython; IPython.embed()
                if VERBOSE:
                    print((indent_str + "  "), "Library: ", filepath, " -> ", lib_path_abs, sep="")
                    # print((indent_str + "  "), lib_block_codes)
                yield from FilePath.visit_from_blend(
                        lib_path_abs,
                        readonly=readonly,
                        temp_remap_cb=temp_remap_cb,
                        recursive=True,
                        block_codes=lib_block_codes,
                        rootdir=rootdir,
                        level=level + 1,
                        lib_visit=lib_visit,
                        )

    # ------------------------------------------------------------------------
    # Direct filepaths from Blocks
    #
    # (no expanding or following references)

    @staticmethod
    def from_block(block, basedir, rootdir, level):
        assert(block.code != b'DATA')
        fn = FilePath._from_block_dict.get(block.code)
        if fn is not None:
            yield from fn(block, basedir, rootdir, level)

    @staticmethod
    def _from_block_IM(block, basedir, rootdir, level):
        # (IMA_SRC_FILE, IMA_SRC_SEQUENCE, IMA_SRC_MOVIE)
        if block[b'source'] not in {1, 2, 3}:
            return
        if block[b'packedfile']:
            return

        yield FilePath(block, b'name', basedir, level), rootdir

    @staticmethod
    def _from_block_LI(block, basedir, rootdir, level):
        if block[b'packedfile']:
            return

        yield FilePath(block, b'name', basedir, level), rootdir

    # _from_block_IM --> {b'IM': _from_block_IM, ...}
    _from_block_dict = {
        k.rpartition("_")[2].encode('ascii'): s_fn.__func__ for k, s_fn in locals().items()
        if isinstance(s_fn, staticmethod)
        if k.startswith("_from_block_")
        }


class bf_utils:
    @staticmethod
    def iter_ListBase(block):
        while block:
            yield block
            block = block.file.find_block_from_offset(block[b'next'])

    def iter_array(block, length=-1):
        assert(block.code == b'DATA')
        import blendfile
        import os
        handle = block.file.handle
        header = block.file.header

        for i in range(length):
            block.file.handle.seek(block.file_offset + (header.pointer_size * i), os.SEEK_SET)
            offset = blendfile.DNA_IO.read_pointer(handle, header)
            sub_block = block.file.find_block_from_offset(offset)
            yield sub_block


# -----------------------------------------------------------------------------
# ID Expand

class ExpandID:
    # fake module
    #
    # TODO:
    #
    # Array lookups here are _WAY_ too complicated,
    # we need some nicer way to represent pointer indirection (easy like in C!)
    # but for now, use what we have.
    #
    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def _expand_generic_material(block):
        array_len = block.get(b'totcol')
        if array_len != 0:
            array = block.get_pointer(b'mat')
            for sub_block in bf_utils.iter_array(array, array_len):
                yield sub_block

    @staticmethod
    def _expand_generic_mtex(block):
        field = block.dna_type.field_from_name[b'mtex']
        array_len = field.dna_size // block.file.header.pointer_size

        for i in range(array_len):
            path = ('mtex[%d]' % i).encode('ascii')
            item = block.get_pointer(path)
            if item:
                yield item.get_pointer(b'tex')
                yield item.get_pointer(b'object')

    @staticmethod
    def _expand_generic_nodetree(block):
        assert(block.dna_type.dna_type_id == b'bNodeTree')

        sdna_index_bNode = block.file.sdna_index_from_id[b'bNode']
        for item in bf_utils.iter_ListBase(block.get_pointer(b'nodes.first')):
            item_type = item.get(b'type', sdna_index_refine=sdna_index_bNode)

            if item_type != 221:  # CMP_NODE_R_LAYERS
                yield item.get_pointer(b'id', sdna_index_refine=sdna_index_bNode)

            # import IPython; IPython.embed()
            # print(item.get(b'name', sdna_index_refine=sdna_index_bNode))
            # print(item.get(b'type', sdna_index_refine=sdna_index_bNode))
            #
    def _expand_generic_nodetree_id(block):
        block_ntree = block.get_pointer(b'nodetree')
        if block_ntree is not None:
            yield from ExpandID._expand_generic_nodetree(block_ntree)

    @staticmethod
    def _expand_generic_animdata(block):
        block_adt = block.get_pointer(b'adt')
        if block_adt:
            yield block_adt.get_pointer(b'action')
        # TODO, NLA

    @staticmethod
    def expand_OB(block):  # 'Object'
        yield from ExpandID._expand_generic_animdata(block)
        yield block.get_pointer(b'data')
        yield block.get_pointer(b'dup_group')

        yield block.get_pointer(b'proxy')
        yield block.get_pointer(b'proxy_group')

    @staticmethod
    def expand_ME(block):  # 'Mesh'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_material(block)

    @staticmethod
    def expand_CU(block):  # 'Curve'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_material(block)

    @staticmethod
    def expand_MB(block):  # 'MBall'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_material(block)

    @staticmethod
    def expand_LA(block):  # 'Lamp'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree_id(block)
        yield from ExpandID._expand_generic_mtex(block)

    @staticmethod
    def expand_MA(block):  # 'Material'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree_id(block)
        yield from ExpandID._expand_generic_mtex(block)

        yield block.get_pointer(b'group')


    @staticmethod
    def expand_TE(block):  # 'Tex'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree_id(block)
        yield block.get_pointer(b'ima')

    @staticmethod
    def expand_WO(block):  # 'World'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree_id(block)
        yield from ExpandID._expand_generic_mtex(block)

    @staticmethod
    def expand_NT(block):  # 'bNodeTree'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree(block)

    @staticmethod
    def expand_SC(block):  # 'Scene'
        yield from ExpandID._expand_generic_animdata(block)
        yield from ExpandID._expand_generic_nodetree_id(block)
        yield block.get_pointer(b'world')

        sdna_index_Base = block.file.sdna_index_from_id[b'Base']
        for item in bf_utils.iter_ListBase(block.get_pointer(b'base.first')):
            yield item.get_pointer(b'object', sdna_index_refine=sdna_index_Base)

    @staticmethod
    def expand_GR(block):  # 'Group'
        sdna_index_GroupObject = block.file.sdna_index_from_id[b'GroupObject']
        for item in bf_utils.iter_ListBase(block.get_pointer(b'gobject.first')):
            yield item.get_pointer(b'ob', sdna_index_refine=sdna_index_GroupObject)

    # expand_GR --> {b'GR': expand_GR, ...}
    expand_funcs = {
        k.rpartition("_")[2].encode('ascii'): s_fn.__func__ for k, s_fn in locals().items()
        if isinstance(s_fn, staticmethod)
        if k.startswith("expand_")
        }


# -----------------------------------------------------------------------------
# Packing Utility


class utils:
    # fake module
    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("%s should not be instantiated" % cls)

    @staticmethod
    def abspath(path, start, library=None):
        import os
        if path.startswith(b'//'):
            # if library:
            #     start = os.path.dirname(abspath(library.filepath))
            return os.path.join(start, path[2:])
        return path

    if __import__("os").sep == '/':
        @staticmethod
        def compatpath(path):
            return path.replace(b'\\', b'/')
    else:
        @staticmethod
        def compatpath(path):
            # keep '//'
            return path[:2] + path[2:].replace(b'/', b'\\')


def pack(blendfile_src, blendfile_dst):

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

    if TIMEIT:
        import time
        t = time.time()

    def temp_remap_cb(filepath, level):
        """
        Create temp files in the destination path.
        """
        filepath = utils.compatpath(filepath)

        if level == 0:
            filepath_tmp = os.path.join(base_dir_dst, os.path.basename(filepath)) + b'@'
        else:
            filepath_tmp = os.path.join(base_dir_dst, SUBDIR, os.path.basename(filepath)) + b'@'

        # only overwrite once (allows us to )
        if filepath_tmp not in path_temp_files:
            shutil.copy(filepath, filepath_tmp)
            path_temp_files.add(filepath_tmp)
        return filepath_tmp

    base_dir_src = os.path.dirname(blendfile_src)
    base_dir_dst = os.path.dirname(blendfile_dst)

    base_dir_dst_subdir = os.path.join(base_dir_dst, SUBDIR)
    if not os.path.exists(base_dir_dst_subdir):
        os.makedirs(base_dir_dst_subdir)

    lib_visit = {}

    for fp, rootdir in FilePath.visit_from_blend(
            blendfile_src,
            readonly=False,
            temp_remap_cb=temp_remap_cb,
            recursive=True,
            lib_visit=lib_visit):

        # assume the path might be relative
        path_rel = utils.compatpath(fp.filepath)
        path_base = path_rel.split(os.sep.encode('ascii'))[-1]
        path_src = utils.abspath(path_rel, fp.basedir)

        # rename in the blend
        path_dst = os.path.join(base_dir_dst_subdir, path_base)
        if fp.level == 0:
            fp.filepath = b"//" + os.path.join(SUBDIR, path_base)
        else:
            fp.filepath = b'//' + path_base

        # add to copylist
        path_copy_files.add((path_src, path_dst))

    del lib_visit

    if TIMEIT:
        print("  Time: %.4f" % (time.time() - t))

    # ----------------
    # Handle File Copy
    blendfile_dst_tmp = temp_remap_cb(blendfile_src, 0)
    shutil.move(blendfile_dst_tmp, blendfile_dst)
    path_temp_files.remove(blendfile_dst_tmp)

    for fn in path_temp_files:
        # strip '@'
        shutil.move(fn, fn[:-1])

    for src, dst in path_copy_files:
        if not os.path.exists(src):
            print("  Source missing! %r" % src)
        else:
            print("  Copying %r -> %r" % (src, dst))
            shutil.copy(src, dst)

    print("  Written:", blendfile_dst)


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
            "-o", "--output", dest="path_dst", metavar='FILE', required=True,
            help="Output file or a directory when multiple inputs are passed")

    return parser


def main():
    import sys

    parser = create_argparse()
    args = parser.parse_args(sys.argv[1:])

    encoding = sys.getfilesystemencoding()

    pack(args.path_src.encode(encoding),
         args.path_dst.encode(encoding))


if __name__ == "__main__":
    main()

