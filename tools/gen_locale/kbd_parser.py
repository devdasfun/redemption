#!/usr/bin/env python3
from typing import Optional, NamedTuple
from xml.etree import ElementTree
from itertools import chain
import sys


# key = (accent, with_key)
DeadKeysType = dict[tuple[str,str], 'DeadKey']

class DeadKey(NamedTuple):
    accent:str
    with_:str
    text:str
    codepoint:int
    deadkeys:DeadKeysType

class Key(NamedTuple):
    scancode:int
    codepoint:int # 0 when text is multi char text ; ord(accent) with deadkey
    text:str # accent with deadkey
    vk:str
    deadkeys:DeadKeysType

    def is_extended(self) -> bool:
        return True if (self.scancode >> 8) == 0xE0 else False

KeymapType = list[Optional[Key]] # always 256 elements
KeymapsType = dict[str, KeymapType] # {mods: keymap}

class KeyLayout(NamedTuple):
    klid:int
    locale_name:str
    display_name:str
    proxy_name:str
    keymaps:KeymapsType
    extra_scancodes:dict[int, Key]
    has_right_ctrl_like_oem8:bool

display_name_to_proxy_name = {
    'Czech': 'cs-CZ',
    'Danish': 'da-DK',
    'German': 'de-DE',
    'Greek': 'el-GR',
    'US': 'en-US',
    'Spanish': 'es-ES',
    'Finnish': 'fi-FI.finnish',
    'French': 'fr-FR',
    'Icelandic': 'is-IS',
    'Italian': 'it-IT',
    'Dutch': 'nl-NL',
    'Norwegian': 'nb-NO',
    'Polish (Programmers)': 'pl-PL.programmers',
    'Portuguese (Brazil ABNT)': 'pt-BR.abnt',
    'Romanian (Legacy)': 'ro-RO',
    'Russian': 'ru-RU',
    'Standard': 'hr-HR',
    'Slovak': 'sk-SK',
    'Swedish': 'sv-SE',
    'Turkish Q': 'tr-TR.q',
    'Ukrainian': 'uk-UA',
    'Slovenian': 'sl-SI',
    'Estonian': 'et-EE',
    'Latvian': 'lv-LV',
    'Lithuanian IBM': 'lt-LT.ibm',
    'Macedonian': 'mk-MK',
    'Faeroese': 'fo-FO',
    'Maltese 47-Key': 'mt-MT.47',
    'Norwegian with Sami': 'se-NO',
    'Kazakh': 'kk-KZ',
    'Kyrgyz Cyrillic': 'ky-KG',
    'Tatar (Legacy)': 'tt-RU',
    'Mongolian Cyrillic': 'mn-MN',
    'United Kingdom Extended': 'cy-GB',
    'Luxembourgish': 'lb-LU',
    'Maori': 'mi-NZ',
    'Swiss German': 'de-CH',
    'United Kingdom': 'en-GB',
    'Latin American': 'es-MX',
    'Belgian French': 'fr-BE.fr',
    'Belgian (Period)': 'nl-BE',
    'Portuguese': 'pt-PT',
    'Serbian (Latin)': 'sr-La',
    'Swedish with Sami': 'se-SE',
    'Uzbek Cyrillic': 'uz-Cy',
    'Inuktitut - Latin': 'iu-La',
    'Canadian French (Legacy)': 'fr-CA',
    'Serbian (Cyrillic)': 'sr-Cy',
    'Canadian French': 'en-CA.fr',
    'Swiss French': 'fr-CH',
    'Irish': 'en-IE.irish',
    'Bosnian (Cyrillic)': 'bs-Cy',
    'Bulgarian (Latin)': 'bg-BG.latin',
    'Czech (QWERTY)': 'cs-CZ.qwerty',
    'German (IBM)': 'de-DE.ibm',
    'Greek (220)': 'el-GR.220',
    'United States-Dvorak': 'en-US.dvorak',
    'Spanish Variation': 'es-ES.variation',
    'Hungarian 101-key': 'hu-HU',
    'Italian (142)': 'it-IT.142',
    'Polish (214)': 'pl-PL',
    'Portuguese (Brazil ABNT2)': 'pt-BR.abnt2',
    'Russian (Typewriter)': 'ru-RU.typewriter',
    'Slovak (QWERTY)': 'sk-SK.qwerty',
    'Turkish F': 'tr-TR.f',
    'Latvian (QWERTY)': 'lv-LV.qwerty',
    'Lithuanian': 'lt-LT',
    'Maltese 48-Key': 'mt-MT.48',
    'Sami Extended Norway': 'se-NO.ext_norway',
    'Belgian (Comma)': 'fr-BE',
    'Finnish with Sami': 'se-SE',
    'Canadian Multilingual Standard': 'en-CA.multilingual',
    'Scottish Gaelic': 'en-IE',
    'Czech Programmers': 'cs-CZ.programmers',
    'Greek (319)': 'el-GR.319',
    'United States-International': 'en-US.international',
    'Sami Extended Finland-Sweden': 'se-SE.ext_finland_sweden',
    'Bulgarian': 'bg-BG',
    'Greek (220) Latin': 'el-GR.220_latin',
    'United States-Dvorak for left hand': 'en-US.dvorak_left',
    'Greek (319) Latin': 'el-GR.319_latin',
    'United States-Dvorak for right hand': 'en-US.dvorak_right',
    'Greek Latin': 'el-GR.latin',
    'Greek Polytonic': 'el-GR.polytonic',
}


def _getattribs(log, node, nodename, attrs):
    if node.tag != nodename:
        raise Exception(f'tag = {node.tag}, but {nodename} expected')

    d = {k:None for k in attrs}

    for k,v in node.attrib.items():
        if k not in d:
            raise Exception(f'{node.tag}: unknown {k}')
        d[k] = v

    # check that all mandatory attributes are extracted
    for k,v in attrs.items():
        if v and d[k] is None:
            raise Exception(f'{node.tag}: {k} is missing')

    log(nodename, d)
    return d.values()


def _parse_deadkeys(log, dead_key_table, deadkeys):
    accent, name = _getattribs(log, dead_key_table, 'DeadKeyTable', {'Accent': True, 'Name': False})
    for result in dead_key_table:
        text, with_ = _getattribs(log, result, 'Result', {'Text': False, 'With': True})
        deadkey = DeadKey(accent=accent, with_=with_, text=text,
                          codepoint=text and ord(text) or 0,
                          deadkeys=None if text else dict())
        k = (accent, with_)
        assert k is not deadkeys
        deadkeys[k] = deadkey
        # double dead keys
        if not text:
            assert len(result) == 1
            _parse_deadkeys(log, result[0], deadkey.deadkeys)
    return accent

def verbose_print(*args):
    print(*args, file=sys.stderr)


_merge_numlock = (
    ('VK_SHIFT VK_NUMLOCK', 'VK_SHIFT'),
    ('VK_SHIFT VK_KANA VK_NUMLOCK', 'VK_SHIFT VK_KANA'),
    ('VK_SHIFT VK_CONTROL VK_MENU VK_NUMLOCK', 'VK_SHIFT VK_CONTROL VK_MENU'),
    ('VK_CONTROL VK_MENU VK_NUMLOCK', 'VK_CONTROL VK_MENU'),
    ('VK_NUMLOCK', ''),
    ('VK_KANA VK_NUMLOCK', 'VK_KANA'),
)

_merge_numlock_capital = (
    ('VK_SHIFT VK_NUMLOCK', 'VK_SHIFT VK_CAPITAL', 'VK_SHIFT VK_CAPITAL VK_NUMLOCK'),
    ('VK_SHIFT VK_CONTROL VK_MENU VK_NUMLOCK', 'VK_SHIFT VK_CONTROL VK_MENU VK_CAPITAL',
     'VK_SHIFT VK_CONTROL VK_MENU VK_CAPITAL VK_NUMLOCK'),
    ('VK_CONTROL VK_MENU VK_NUMLOCK', 'VK_CONTROL VK_MENU VK_CAPITAL',
     'VK_CONTROL VK_MENU VK_CAPITAL VK_NUMLOCK'),
    ('VK_NUMLOCK', 'VK_CAPITAL', 'VK_CAPITAL VK_NUMLOCK'),
)

def parse_xml_layout(filename, log=verbose_print):
    # VK_MENU = Alt
    # VK_CAPITAL = CapsLock
    # VK_CONTROL + VK_MENU = AltGr
    keymaps = {k:[None]*256 for k in (
        '',
        'VK_SHIFT',
        'VK_SHIFT VK_CONTROL',
        'VK_SHIFT VK_CAPITAL',
        'VK_SHIFT VK_NUMLOCK',
        'VK_SHIFT VK_KANA',
        'VK_SHIFT VK_OEM_8',
        'VK_SHIFT VK_CONTROL VK_MENU',
        'VK_SHIFT VK_CONTROL VK_KANA',
        'VK_SHIFT VK_KANA VK_NUMLOCK',
        'VK_SHIFT VK_CONTROL VK_MENU VK_CAPITAL',
        'VK_SHIFT VK_CONTROL VK_MENU VK_NUMLOCK',
        'VK_CONTROL',
        'VK_CONTROL VK_MENU',
        'VK_CONTROL VK_KANA',
        'VK_CONTROL VK_MENU VK_NUMLOCK',
        'VK_CONTROL VK_MENU VK_CAPITAL',
        'VK_CAPITAL',
        'VK_NUMLOCK',
        'VK_OEM_8',
        'VK_KANA',
        'VK_KANA VK_NUMLOCK',
    )}
    extra_scancodes = {}

    root = ElementTree.parse(filename).getroot()
    klid, locale_name, display_name = _getattribs(log, root[0], 'metadata', {'KLID': True,
                                                                             'LocaleName': True,
                                                                             'LayoutDisplayName': True})
    right_ctrl_like_oem8 = False
    has_oem8_key = False
    for pk in root[1]:
        sc, vk, _ = _getattribs(log, pk, 'PK', {'SC': True, 'VK': True, 'Name': False})
        sc = int(sc, 16)

        # 0xE0XX -> extended
        # 0xE11D -> pause

        assert sc & 0xff
        # assert (sc & 0xff) <= 0x7f
        assert (sc >> 8) in (0, 0xE0, 0xE1)

        # Pause
        if sc > 0xE100:
            assert sc == 0xE11D
            extra_scancodes[sc] = Key(scancode=sc, codepoint=0, text='', vk=vk, deadkeys=dict())
            continue

        if not pk and vk == 'VK_OEM_8':
            # assume that VK_OEM_8 is set after dead keys
            assert has_oem8_key
            assert sc == 0xE01D # right ctrl
            right_ctrl_like_oem8 = sc

        sc = (sc & 0x7f) | (0x80 if sc >> 8 else 0)

        if not pk:
            keys = keymaps['']
            assert sc not in keys
            keys[sc] = Key(scancode=sc, codepoint=0, text='', vk=vk, deadkeys=dict())
            continue

        for result in pk:
            text, codepoint, vk, with_ = _getattribs(log, result, 'Result', {'Text': False,
                                                                             'TextCodepoints': False,
                                                                             'VK': False,
                                                                             'With': False})
            keys = keymaps[with_ or '']

            if with_ and ('VK_OEM_8' in with_):
                assert not right_ctrl_like_oem8
                has_oem8_key = True

            if sc in keys:
                raise Exception(f'key {sc} ({text}/{codepoint}) already set')

            if text or codepoint:
                if codepoint:
                    assert not text
                    codepoint = int(codepoint, 16)
                    text = codepoint.to_bytes((codepoint.bit_length() + 7) // 8, byteorder='big'
                                              ).decode('utf8')
                elif len(text) == 1:
                    codepoint = ord(text)
                else:
                    # multi char
                    codepoint = 0

                keys[sc] = Key(scancode=sc, codepoint=codepoint, text=text, vk=vk, deadkeys=dict())

            # dead keys
            elif len(result):
                assert not vk
                assert len(result) == 1
                deadkeys = dict()
                accent = _parse_deadkeys(log, result[0], deadkeys)
                assert len(accent) == 1
                assert deadkeys
                keys[sc] = Key(scancode=sc, codepoint=ord(accent), text=accent, vk=vk, deadkeys=deadkeys)


    # new keymap: shiftlock + numlock
    for num_mod, caps_mod, final_mod in _merge_numlock_capital:
        assert final_mod not in keymaps
        caps_keymap = keymaps[caps_mod]
        numlock_keymap = keymaps[num_mod]
        keymap = [None] * 256
        for i in range(256):
            k = caps_keymap[i]
            knum = numlock_keymap[i]
            assert not (k and knum)
            keymap[i] = k or knum
        keymaps[final_mod] = keymap

    # merge mod to numlock mod
    for num_mod, merged_mod in _merge_numlock:
        keymap = keymaps[merged_mod]
        numlock_keymap = keymaps[num_mod]
        for i in range(256):
            k = keymap[i]
            knum = numlock_keymap[i]
            assert not (k and knum)
            if k:
                numlock_keymap[i] = k

    return KeyLayout(klid, locale_name, display_name,
                     display_name_to_proxy_name.get(display_name, None),
                     keymaps, extra_scancodes,
                     right_ctrl_like_oem8)

def _accu_scancodes(strings:list[str], map:list[Key]):
    for i,k in enumerate(map):
        if k:
            text = k.text
            if k.codepoint < 32:
                if 0x07 <= k.codepoint <= 0x0D:
                    text = ('\\a', '\\b', '\\t', '\\n', '\\v', '\\f', '\\r')[k.codepoint - 0x07]
                elif k.codepoint:
                    text = ''
            # del
            elif k.codepoint == 127:
                text = ''
            strings.append(f"  0x{i:02X}: codepoint=0x{k.codepoint:04x} text='{text}' vk='{k.vk}'\n")
            if k.deadkeys:
                strings.append('       DeadKeys: ')
                prefix = ''
                for dk in k.deadkeys.values():
                    strings.append(f'{prefix}{dk.accent} + {dk.text} => {dk.codepoint}\n')
                    prefix = '                 '
        else:
            strings.append(f"  0x{i:02X} -\n")

def print_layout(layout:KeyLayout, printer=sys.stdout.write):
    strings = [f'KLID: {layout.klid}\nLocalName: {layout.locale_name}\nDisplayName: {layout.display_name}\n']

    for mapname,map in layout.keymaps.items():
        strings.append(f'{mapname or "normal"} (0x00)\n')
        _accu_scancodes(strings, map)

    strings.append('extra:\n')
    for i,k in layout.extra_scancodes.items():
        strings.append(f"  0x{i:04X} Key(vk='{k.vk}')\n")

    printer(''.join(strings))


def null_fn(*args):
    pass

def parse_argv(argv:Optional[list] = None, printer=sys.stdout.write) -> list[KeyLayout]:
    argv = argv if argv is not None else sys.argv
    log = null_fn
    iargv = 1

    if len(argv) > 1 and argv[1] == '-v':
        log = verbose_print
        iargv += 1

    if len(argv) == iargv:
        print(argv[0], '[-v] layout.xml...', file=sys.stderr)
        exit(1)

    layouts:list[KeyLayout] = []
    for filename in argv[iargv:]:
        log('filename:', filename)
        layout = parse_xml_layout(filename, log)
        layouts.append(layout)
        if log == verbose_print:
            print_layout(layout, printer)

    return layouts
