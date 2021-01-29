import os
import logging
import json
from bagit_profile import *
from bdbag import guess_mime_type


# We are subclassing the bagit_profile.Profile class, specifically to override/patch the validate_serialization method.
# Ideally, at some point the base bagit_profile.Profile.validate_serialization method could be fixed and this would no
# longer be necessary...
class BDBProfile(Profile):

    def __init__(self, url, profile=None, ignore_baginfo_tag_case=False):
        super(BDBProfile, self).__init__(url, profile, ignore_baginfo_tag_case)

    # Patching validate_serialization function is necessary because of the way the 'Accept-Serialization' is tested.
    # The current code (as of 1.3.1) does not properly inspect all fields of the tuple returned by mimetypes.guess_type;
    # e.g. "application/x-tar+gzip" is passed only because of "application/x-tar" being present. Also, the exception
    # detail string returned is incorrect for the condition being handled.
    #
    def validate_serialization(self, path_to_bag):
        # First, perform the two negative tests.
        if not exists(path_to_bag):
            raise IOError("Can't find file %s" % path_to_bag)
        if self.profile["Serialization"] == "required" and isdir(path_to_bag):
            self._fail(
                "%s: Bag serialization is required but Bag is a directory."
                % path_to_bag
            )
        if self.profile["Serialization"] == "forbidden" and isfile(path_to_bag):
            self._fail(
                "%s: Bag serialization is forbidden but Bag appears is a file."
                % path_to_bag
            )

        # Then test to see whether the Bag is serialized (is a file) and whether the mimetype is one
        # of the allowed types.
        if (
            self.profile["Serialization"] == "required"
            or self.profile["Serialization"] == "optional"
            and isfile(path_to_bag)
        ):
            bag_path, bag_file = os.path.split(path_to_bag)
            mimetype = guess_mime_type(bag_file)
            if mimetype not in self.profile['Accept-Serialization']:
                self._fail(
                    "%s: Bag serialization type \"%s\" is not in the list of allowed values." % (path_to_bag, mimetype))

        # If we have passed the serialization tests, return True.
        return True
