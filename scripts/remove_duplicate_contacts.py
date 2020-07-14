# coding=utf-8

from copy import copy
from itertools import combinations

import sys
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from Acquisition import aq_inner
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from plone.behavior.interfaces import IBehavior
from z3c.relationfield.relation import RelationValue
from zc.relation.interfaces import ICatalog
from zope.component import getUtility
from zope.component.hooks import setSite
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import urwid
#import locale
#locale.setlocale(locale.LC_ALL, '')


def get_fields(portal_type):
    fti = getUtility(IDexterityFTI, name=portal_type)
    schema = fti.lookupSchema()
    fields = schema.names()
    for bname in fti.behaviors:
        factory = getUtility(IBehavior, bname)
        behavior = factory.interface
        fields += behavior.names()
    return fields


CONTACT_FIELDS = (
    'phone',
    'cell_phone',
    'fax',
    'email',
    'website',
)
ADDRESS_FIELDS = (
    'number',
    'street',
    'additional_address_details',
    'zip_code',
    'city',
    'region',
    'country',
)

help_text = [
    "Suppression de contacts en doublon",
    "\n",
    "Pour chaque proposition, choisir une des 3 options",
    "\n",
    "Pour quitter le script, appuyer sur la lettre 'q'",
]


class Match:
    def __init__(self, contestant_1, contestant_2):
        self.contestant_1 = contestant_1
        self.contestant_2 = contestant_2
        self.distance = self.damerau_levenshtein(
            contestant_1.get_full_title().lower().strip(),
            contestant_2.get_full_title().lower().strip(),
        )
        self.winner = None
        self.loser = None

    def __str__(self):
        return "{}: {} X {}".format(
            id(self),
            self.contestant_1.get_full_title().lower().strip(),
            self.contestant_2.get_full_title().lower().strip(),
        )

    def get_contact_info(self, contact):
        info = []
        for field_name in CONTACT_FIELDS:
            value = getattr(contact, field_name, None)
            if value:
                info.append(value.encode("utf8"))
        return ", ".join(info)

    def get_address_info(self, contact):
        info = []
        for field_name in ADDRESS_FIELDS:
            value = getattr(contact, field_name, None)
            if value:
                info.append(value.encode("utf8"))
        return ", ".join(info)

    def get_content(self, contact):
        titles = [child.Title() for child in contact.values()]
        if titles:
            return "{0} élément(s)\n{1}".format(
                len(titles),
                "\n".join(["  - {0}".format(title) for title in titles]),
            )
        else:
            return "vide"

    def get_full_info(self, contact):
        return "{0}\ndate de création: {1}\ncontact: {2}\nadresse: {3}\ncontenu: {4}".format(
            contact.get_full_title().encode("utf8"),
            contact.creation_date.strftime("%d/%m/%Y %H:%M:%S"),
            self.get_contact_info(contact),
            self.get_address_info(contact),
            self.get_content(contact),
        )

    @staticmethod
    def damerau_levenshtein(string_1, string_2):
        """
        Calculates the Damerau-Levenshtein distance between two strings.
        In addition to insertions, deletions and substitutions,
        Damerau-Levenshtein considers adjacent transpositions.
        This version is based on an iterative version of the Wagner-Fischer algorithm.
        Usage::
            >>> damerau_levenshtein('kitten', 'sitting')
            3
            >>> damerau_levenshtein('kitten', 'kittne')
            1
            >>> damerau_levenshtein('', '')
            0
        """
        if string_1 == string_2:
            return 0

        len_1 = len(string_1)
        len_2 = len(string_2)

        if len_1 == 0:
            return len_2
        if len_2 == 0:
            return len_1

        if len_1 > len_2:
            string_2, string_1 = string_1, string_2
            len_2, len_1 = len_1, len_2

        prev_cost = 0
        d0 = [i for i in range(len_2 + 1)]
        d1 = [j for j in range(len_2 + 1)]
        dprev = d0[:]

        s1 = string_1
        s2 = string_2

        for i in range(len_1):
            d1[0] = i + 1
            for j in range(len_2):
                cost = d0[j]

                if s1[i] != s2[j]:
                    # substitution
                    cost += 1

                    # insertion
                    x_cost = d1[j] + 1
                    if x_cost < cost:
                        cost = x_cost

                    # deletion
                    y_cost = d0[j + 1] + 1
                    if y_cost < cost:
                        cost = y_cost

                    # transposition
                    if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                        transp_cost = dprev[j - 1] + 1
                        if transp_cost < cost:
                            cost = transp_cost
                d1[j + 1] = cost

            dprev, d0, d1 = d0, d1, dprev

        return d0[-1]


class Ring:
    def __init__(self):
        self.matches = self.get_matches()
        self.current_match = None

    def get_matches(self):
        matches = []
        catalog = api.portal.get_tool("portal_catalog")

        for contact_type in ('person', 'organization'):
            contacts = [
                brain.getObject()
                for brain
                in catalog(portal_type=contact_type)
            ]
            for left, right in combinations(contacts, 2):
                match = Match(left, right)
                matches.append(match)

        matches.sort(key=lambda x: x.distance, reverse=True)
        return matches

    def set_next_match(self):
        if self.matches:
            self.current_match = self.matches.pop()
            return True
        else:
            return False

    def merge_match(self):
        """
        """
        self.update_remaining_matches()
        self._remove_content_object(
            self.current_match.loser,
            self.current_match.winner,
        )
        transaction.commit()
        app._p_jar.sync()

    def update_remaining_matches(self):
        """
        Replace the losing contact by the winning one in remaining matches.
        """
        current_winner = self.current_match.winner
        current_loser = self.current_match.loser

        for match in self.matches:
            if match.contestant_1 == current_loser:
                match.contestant_1 = current_winner
            elif match.contestant_2 == current_loser:
                match.contestant_2 = current_winner

        to_remove = [match for match in self.matches
                     if match.contestant_1 == match.contestant_2]
        for match in to_remove:
            self.matches.remove(match)

    def _remove_content_object(self, content, canonical):
        """Move subcontents and references of merged content and remove it
        """
        self._transfer_back_references(content, canonical)
        if len(content.keys()) > 0:
            cb = content.manage_cutObjects(content.keys())
            canonical.manage_pasteObjects(cb)
        api.content.delete(content)

    def get_back_references(self, source_object):
        """ Return back references from source object on specified attribute_name """
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        result = []
        try:
            source_intid = intids.getId(aq_inner(source_object))
        except KeyError:
            return result
        for rel in catalog.findRelations({'to_id': source_intid}):
            from_id = getattr(rel, '_from_id', None)
            if not from_id:
                from_id = rel.from_id
            try:
                obj = intids.queryObject(from_id)
            except KeyError:

                obj = None

            if obj:
                result.append({'obj': obj,
                               'attribute': rel.from_attribute})
        return result

    def _transfer_back_references(self, content, canonical):
        """Update back references of removed objects
        """
        intids = getUtility(IIntIds)
        try:
            canonical_intid = intids.getId(canonical)
        except KeyError:
            return
        back_references = self.get_back_references(content)
        # for each back reference...
        for back_reference in back_references:
            from_obj = back_reference['obj']
            attribute = back_reference['attribute']
            value = getattr(from_obj, attribute)
            # we remove relation to content,
            # and replace it with a relation to canonical (if there is no canonical yet)
            if isinstance(value, (tuple, list)):
                canonical_path = '/'.join(canonical.getPhysicalPath())
                canonical_already_in_list = any([item.to_path == canonical_path for item in value])
                for index, item in enumerate(copy(value)):
                    if item.to_path == '/'.join(content.getPhysicalPath()):
                        value.remove(item)
                        if not canonical_already_in_list:
                            value.insert(index, RelationValue(canonical_intid))
                        break

                setattr(from_obj, attribute, value)
            else:
                setattr(from_obj, attribute, RelationValue(canonical_intid))

            modified(from_obj)


def main_print_loop(app):
    # Use Zope application server user database (not plone site)
    admin = app.acl_users.getUserById("admin")
    newSecurityManager(None, admin)

    # pass the Plone site id as an argument to the script
    site_name = sys.argv[-1] if len(sys.argv) > 3 else "Plone"
    site = getattr(app, site_name)
    setSite(site)

    ring = Ring()

    print
    print "=================================="
    print "Suppression de contacts en doublon"
    print "=================================="
    print

    while ring.set_next_match():
        match = ring.current_match
        print
        print match.get_full_info(match.contestant_1)
        print match.get_full_info(match.contestant_2)
        while 1:
            answer = raw_input("conserver [1], conserver [2], [i]gnorer, [q]uitter: ").lower().strip()
            if answer == '1':
                match.winner = match.contestant_1
                match.loser = match.contestant_2
                ring.merge_match()
                break
            elif answer == '2':
                match.winner = match.contestant_2
                match.loser = match.contestant_1
                ring.merge_match()
                break
            elif answer == 'i':
                break
            elif answer == 'q':
                exit(0)


def main_urwid(app):
    # Use Zope application server user database (not plone site)
    admin = app.acl_users.getUserById("admin")
    newSecurityManager(None, admin)

    # pass the Plone site id as an argument to the script
    site_name = sys.argv[-1] if len(sys.argv) > 3 else "Plone"
    site = getattr(app, site_name)
    setSite(site)

    ring = Ring()
    ring.set_next_match()
    match = ring.current_match

    help = urwid.Text(help_text, align="center")
    div1 = urwid.Divider()
    contestant_1 = urwid.Padding(urwid.Text(match.get_full_info(match.contestant_1)), 'left', 40)
    contestant_split = urwid.Padding(urwid.Text(u""), 'center', 18)
    contestant_2 = urwid.Padding(urwid.Text(match.get_full_info(match.contestant_2)), 'right', 40)
    contestants = urwid.Columns([contestant_1, (18, contestant_split), contestant_2])
    div2 = urwid.Divider()
    button_keep_1 = urwid.Padding(urwid.Button(u'Conserver n° 1'), 'left', 18)
    button_next_match = urwid.Padding(urwid.Button(u'Suivant'.center(14)), 'center', 18)
    button_keep_2 = urwid.Padding(urwid.Button(u'Conserver n° 2'), 'right', 18)
    choices = urwid.Columns([
        button_keep_1,
        button_next_match,
        button_keep_2,
    ])

    def set_next():
        if not ring.set_next_match():
            raise urwid.ExitMainLoop()
        match = ring.current_match
        contestant_1.original_widget.set_text(match.get_full_info(match.contestant_1))
        contestant_2.original_widget.set_text(match.get_full_info(match.contestant_2))

    def next_match(button):
        set_next()

    def keep_1(button):
        match = ring.current_match
        match.winner = match.contestant_1
        match.loser = match.contestant_2
        ring.merge_match()
        set_next()

    def keep_2(button):
        match = ring.current_match
        match.winner = match.contestant_2
        match.loser = match.contestant_1
        ring.merge_match()
        set_next()

    def exit_on_q(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    urwid.connect_signal(button_keep_1.original_widget, 'click', keep_1)
    urwid.connect_signal(button_next_match.original_widget, 'click', next_match)
    urwid.connect_signal(button_keep_2.original_widget, 'click', keep_2)

    body = [
        help,
        div1,
        contestants,
        div2,
        choices,
    ]

    listbox = urwid.ListBox(urwid.SimpleFocusListWalker(body))

    padding = urwid.Padding(listbox, left=3, right=3)

    loop = urwid.MainLoop(padding, unhandled_input=exit_on_q)
    loop.run()


if "app" in locals():
    # main_print_loop(app)
    main_urwid(app)
