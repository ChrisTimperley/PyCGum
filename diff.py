#!/usr/bin/env
#
#
#
#
#
from utility import *
import json
import tempfile
from subprocess import Popen

class Action(object):
    @staticmethod
    def from_json(jsn):
        return ({
            'insert': Insert,
            'remove': Remove,
            'update': Update,
            'move': Move,
            'delete': Delete
        })[jsn['action']].from_json(jsn)

    def __init__(self, parent_id):
        self.__parent_id = int(parent_id)

    def parent_id(self):
        return self.__parent_id
    def set_parent_id(self, x):
        self.__parent_id = x
        return x

# Gives the ID of the node in the original tree that was deleted.
class Delete(Action):
    @staticmethod
    def from_json(jsn):
        return Delete(jsn['tree'])

    def __str__(self):
        return "DEL(%d)" % self.parent_id()

class Move(Action):
    @staticmethod
    def from_json(jsn):
        return Move(jsn['tree'], jsn['parent'], jsn['at'])

    def __init__(self, tree_id, parent_id, position):
        super().__init__(parent_id)
        self.__tree_id = tree_id
        self.__position = position

    def tree_id(self):
        return self.__tree_id
    def position(self):
        return self.__position

    def __str__(self):
        return "MOV(%d, %d, %d)" % \
            (self.tree_id(), self.parent_id(), self.position())

# Doesn't handle insert root
class Insert(Action):
    @staticmethod
    def from_json(jsn):
        return Insert(jsn['tree'], jsn['parent'], jsn['at'])

    def __init__(self, child_id, parent_id, position):
        super().__init__(parent_id)
        self.__child_id = child_id
        self.__position = position

    def correct(self, id_map):
        post_parent_id = self.parent_id()
        id_map[post_parent_id] = \
            self.set_parent_id(id_map[post_parent_id] - 1)
        return id_map

    def child_id(self):
        return self.__child_id
    def set_child_id(self, x):
        self.__child_id = x
    def position(self):
        return self.__position

    def __str__(self):
        return "INS(%d, %d, %d)" % \
            (self.child_id(), self.parent_id(), self.position())

# TODO: Fix me! I should remove a node from a parent at a given ID
class Remove(Action):
    @staticmethod
    def from_json(jsn):
        assert not ('at' in jsn)
        return Remove(jsn['parent'])

    # To rollback the effects of a Remove operation, we shift all IDs after X
    # forward by the size of X, simulating an insertion.
    def correct(self, id_map):
        parent_id = id_map[self.parent_id()] # we could destructively remove here?
        SIZE = 1 # TODO: For now we assume the size is 1
        for (post_id, curr_id) in id_map.items():
            if curr_id > parent_id:
                id_map[post_id] += SIZE
        self.set_parent_id(id_map[post_id])

    def __str__(self):
        return "REM(%d)" % self.parent_id()

class Update(Action):
    @staticmethod
    def from_json(jsn):
        return Update(jsn['tree'], jsn['label'])

    def __init__(self, parent_id, label):
        super().__init__(parent_id)
        self.__label = label

    # Update actions have no effect on the IDs of successive edits, but we do
    # need to fetch the altered ID from the map for this action.
    def correct(self, id_map):
        self.set_parent_id(id_map[self.parent_id()])

    def label(self):
        return self.__label

    def __str__(self):
        return "UPD(%d, %s)" % (self.parent_id(), self.label())

class Diff(object):
    @staticmethod
    def from_source_files(fn_from, fn_to):
        tmp_f = tempfile.NamedTemporaryFile()
        assert Popen(("gumtree jsondiff \"%s\" \"%s\"" % (fn_from, fn_to)), \
                     shell=True, stdin=FNULL, stdout=tmp_f).wait() == 0
        return Diff.from_file(tmp_f.name)

    @staticmethod
    def from_file(fn):
        with open(fn, 'r') as f:
            return Diff.from_json(json.load(f))

    @staticmethod
    def from_json(jsn):
        return Diff([Action.from_json(action) for action in jsn])

    def __init__(self, actions):
        self.__actions = actions

    # Fixes the IDs in the patch, such that a theoretically executable
    # patch is produced
    def correct(self):
        # Create a map, from the original IDs referred to in the program
        # to their position at the current point of unrolling.
        id_map = {action.parent_id() for action in self.__actions}
        id_map = {pid: pid for pid in id_map}

        # Separate the edits by type. Deal with deletions and removals first,
        # then handle inserts, and finally, do nothing with the updates.
        inserts = []
        deletions = []
        removals = []
        updates = []
        for action in self.__actions:
            ({
                Insert: inserts,
                Delete: deletions,
                Remove: removals,
                Update: updates
            })[action.__class__].append(action)

        # First, correct the deletions by going forward and shifting the IDs
        # of future edits (after that ID) back by one.
        for deletion in deletions:
            at = deletion.parent_id()
            at = id_map.pop(at)
            deletion.set_parent_id(at)
            for (original_id, current_id) in id_map.items():
                if current_id > at:
                    id_map[original_id] -= 1

        # HANDLE REMOVALS
        # SHOULD BE SIMILAR TO THE ABOVE

        # Handle insertions
        for insert in inserts:
            parent = insert.parent_id()
            child = insert.child_id()
    
        # Put the actions together in the correct order
        self.__actions = deletions + updates

    def __str__(self):
        return '\n'.join(map(str, self.__actions))
