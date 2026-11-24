#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tuxracersettings.pyw
====================
Graphical editor for the Tux Racer 0.61 ``options.txt`` configuration file.

Features
--------
* Pure standard library (tkinter) — no external dependencies.
* Two hardcoded interface languages: English and Russian.
* Tux Racer snow theme: light blue + white, with black/blue accents.
* Animated falling snow in the header.
* Edits the configuration file in place, preserving all comments
  and the original ordering of directives.
* Adds any missing directives at the end of the file on save.

Usage
-----
Just double-click the file (on Windows the ``.pyw`` extension hides
the console). The script looks for ``options.txt`` next to itself,
then in the current working directory, then in the usual
``~/.tuxracer`` / ``~/.tuxracer-0.61`` locations.
"""

import math
import os
import random
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

# ===========================================================================
# Colour palette — Tux Racer snow theme
# ===========================================================================
C_BG_TOP        = '#DCEFFB'   # pale ice blue (top of gradient)
C_BG_BOTTOM     = '#FFFFFF'   # white (bottom of gradient)
C_PANEL         = '#FFFFFF'
C_PANEL_BORDER  = '#A9CDE5'
C_HEADER        = '#0F3D6E'   # deep night-sky blue (text on light bg)
C_ACCENT        = '#2E78C2'   # mid blue (buttons)
C_ACCENT_DARK   = '#0F3D6E'
C_ACCENT_HOVER  = '#1E5C9C'
C_TEXT          = '#0A2540'   # near-black
C_TEXT_SOFT     = '#44607E'
C_TEXT_LIGHT    = '#FFFFFF'
C_SNOW          = '#F4FAFF'
C_SNOWFLAKE     = '#FFFFFF'
C_SNOWFLAKE_OUT = '#B6D7EE'
C_TAB_BG        = '#EAF4FC'
C_TAB_ACTIVE    = '#FFFFFF'
C_TAB_BORDER    = '#9BC2E0'
C_DANGER        = '#B43A3A'
C_DISABLED      = '#9FB3C4'

# ===========================================================================
# Font selection \u2014 pick a scalable font that actually exists on the host.
# Tkinter falls back to a bitmap "fixed" font when a family is missing, and
# that bitmap font typically lacks Cyrillic glyphs. We probe a list of
# candidates and use the first one Tk resolves to a real scalable family.
# ===========================================================================
_FONT_PROBE = {}
def _pick_font(candidates, want_mono=False, root=None):
    """Return the first font family from *candidates* that Tk can render
    as a real (non-bitmap) scalable font. Falls back to TkDefaultFont.
    If *root* is None, a temporary Tk root is created (and destroyed)."""
    cache_key = 'mono' if want_mono else 'sans'
    if cache_key in _FONT_PROBE:
        return _FONT_PROBE[cache_key]
    chosen = None
    owns_root = False
    if root is None:
        try:
            root = tk.Tk()
            root.withdraw()
            owns_root = True
        except Exception:
            root = None
    if root is not None:
        for name in candidates:
            try:
                f = tkfont.Font(root=root, family=name, size=10)
                actual = f.actual()['family'].lower()
                # reject bitmap / generic fallbacks
                if actual and actual not in ('fixed', 'nil', '') and name.lower() not in ('fixed',):
                    # verify it actually measures some glyphs (incl. Cyrillic)
                    if f.measure('ABCDabcd\u0410\u0411\u0412\u0430\u0431\u0432') > 0:
                        chosen = name
                        break
            except Exception:
                continue
        if owns_root:
            root.destroy()
    if chosen is None:
        chosen = 'TkFixedFont' if want_mono else 'TkDefaultFont'
    _FONT_PROBE[cache_key] = chosen
    return chosen

# Will be initialised after Tk root exists; sensible defaults here.
F_SANS  = 'TkDefaultFont'
F_SANSB = 'TkDefaultFont'
F_MONO  = 'TkFixedFont'

def _init_fonts(root=None):
    global F_SANS, F_SANSB, F_MONO
    F_SANS  = _pick_font(['Segoe UI', 'Trebuchet MS', 'DejaVu Sans',
                          'Liberation Sans', 'Noto Sans', 'Arial',
                          'Helvetica', 'Nimbus Sans'], root=root)
    F_SANSB = F_SANS  # same family, we add 'bold' weight in the font tuple
    F_MONO  = _pick_font(['Consolas', 'DejaVu Sans Mono', 'Liberation Mono',
                          'Courier New', 'Courier', 'Nimbus Mono'],
                         want_mono=True, root=root)

def F(size, bold=False, italic=False):
    """Build a Tk font tuple using the resolved sans family."""
    fam = F_SANS
    weight = 'bold' if bold else 'normal'
    slant = 'italic' if italic else 'roman'
    return (fam, size, weight, slant)

def FM(size):
    """Build a Tk font tuple using the resolved mono family."""
    return (F_MONO, size)

# ===========================================================================
# Hardcoded localisation \u2014 two languages (en, ru)
# ===========================================================================
L = {
    'en': {
        'title':        'Tux Racer Settings',
        'subtitle':     'Snowy Mountain Configuration',
        'file_label':   'Config file:',
        'browse':       'Browse...',
        'new_file':     'New',
        'lang':         'Language:',
        'tab_display':  'Display',
        'tab_controls': 'Controls',
        'tab_joystick': 'Joystick',
        'tab_audio':    'Audio',
        'tab_graphics': 'Graphics',
        'tab_advanced': 'Advanced',
        'save':         'Save',
        'save_as':      'Save As...',
        'reset':        'Reset',
        'close':        'Close',
        'expert':       '[EXPERT]',
        'range_hint':   'range',
        'default_hint': 'default',

        # Display
        'data_dir':              'Data directory',
        'fullscreen':            'Full-screen mode',
        'x_resolution':          'Horizontal resolution',
        'y_resolution':          'Vertical resolution',
        'bpp_mode':              'Colour depth',
        'capture_mouse':         'Capture mouse in window',
        'force_window_position': 'Force window to position (0,0)',
        'view_mode':             'Default camera view',
        # Controls
        'quit_key':              'Quit race',
        'turn_left_key':         'Turn left',
        'turn_right_key':        'Turn right',
        'trick_modifier_key':    'Trick modifier',
        'brake_key':             'Brake',
        'paddle_key':            'Paddle / Flap',
        'jump_key':              'Jump',
        'reset_key':             'Reset position',
        'follow_view_key':       'Camera: Follow',
        'behind_view_key':       'Camera: Behind',
        'above_view_key':        'Camera: Above',
        'screenshot_key':        'Screenshot',
        'pause_key':             'Pause',
        # Joystick
        'joystick_paddle_button':   'Paddle button',
        'joystick_brake_button':    'Brake button',
        'joystick_jump_button':     'Jump button',
        'joystick_trick_button':    'Trick button',
        'joystick_continue_button': 'Continue button',
        'joystick_x_axis':          'X axis (turning)',
        'joystick_y_axis':          'Y axis (paddle/brake)',
        # Audio
        'no_audio':           'Disable all audio',
        'sound_enabled':      'Sound effects',
        'music_enabled':      'Music',
        'sound_volume':       'Sound volume',
        'music_volume':       'Music volume',
        'audio_freq_mode':    'Audio frequency',
        'audio_format_mode':  'Bits per sample',
        'audio_stereo':       'Stereo',
        'audio_buffer_size':  'Audio buffer size',
        # Graphics
        'display_fps':                'Show FPS',
        'course_detail_level':        'Course detail level',
        'forward_clip_distance':      'Forward clip distance',
        'backward_clip_distance':     'Backward clip distance',
        'tree_detail_distance':       'Tree detail distance',
        'terrain_blending':           'Terrain blending',
        'perfect_terrain_blending':   'Perfect terrain blending',
        'terrain_envmap':             'Ice environment map (shine)',
        'disable_fog':                'Disable fog',
        'draw_tux_shadow':            "Tux's shadow",
        'tux_sphere_divisions':       'Tux sphere divisions',
        'tux_shadow_sphere_divisions':'Shadow sphere divisions',
        'draw_particles':             'Snow particles',
        'track_marks':                'Track marks in snow',
        'ui_snow':                    'Falling snow on UI',
        'nice_fog':                   'Nice fog (GL_NICEST)',
        'use_cva':                    'Use compiled vertex arrays',
        'cva_hack':                   'CVA hack (driver workaround)',
        'use_sphere_display_list':    'Use sphere display list',
        'do_intro_animation':         'Intro animation',
        'mipmap_type':                'Mipmap / texture filter',
        # Advanced
        'ode_solver':           'ODE solver',
        'fov':                  'Field of view (degrees)',
        'debug':                'Debug flags',
        'warning_level':        'Warning level',
        'write_diagnostic_log': 'Write diagnostic_log.txt',

        # Enum labels
        'bpp_system':  'System default',
        'bpp_16':      '16 bpp',
        'bpp_32':      '32 bpp',
        'view_behind': 'Behind',
        'view_follow': 'Follow',
        'view_above':  'Above',
        'freq_11025':  '11025 Hz',
        'freq_22050':  '22050 Hz',
        'freq_44100':  '44100 Hz',
        'bits_8':  '8 bits',
        'bits_16': '16 bits',
        'mipmap_0': 'GL_NEAREST',
        'mipmap_1': 'GL_LINEAR',
        'mipmap_2': 'NEAREST_MIPMAP_NEAREST',
        'mipmap_3': 'LINEAR_MIPMAP_NEAREST',
        'mipmap_4': 'NEAREST_MIPMAP_LINEAR',
        'mipmap_5': 'LINEAR_MIPMAP_LINEAR',
        'ode_0': 'Modified Euler (fast)',
        'ode_1': 'Runge-Kutta (2,3)',
        'ode_2': 'Runge-Kutta (4,5) (accurate)',

        # Messages
        'saved':          'Configuration saved successfully.',
        'save_error':     'Error saving file:',
        'no_file':        'No configuration file is loaded. Use "Browse..." to open one.',
        'reset_confirm':  'Reset all values back to the file on disk?',
        'file_not_found': 'File not found:',
        'invalid_value':  'Invalid value for',
        'unsaved':        'There are unsaved changes. Close anyway?',
        'key_hint':       'Space-separated key names, e.g.  q escape',
    },
    'ru': {
        'title':        'Настройки Tux Racer',
        'subtitle':     'Конфигурация Снежных Гор',
        'file_label':   'Файл конфигурации:',
        'browse':       'Обзор...',
        'new_file':     'Создать',
        'lang':         'Язык:',
        'tab_display':  'Экран',
        'tab_controls': 'Управление',
        'tab_joystick': 'Джойстик',
        'tab_audio':    'Звук',
        'tab_graphics': 'Графика',
        'tab_advanced': 'Дополнительно',
        'save':         'Сохранить',
        'save_as':      'Сохранить как...',
        'reset':        'Сбросить',
        'close':        'Закрыть',
        'expert':       '[ЭКСПЕРТ]',
        'range_hint':   'диапазон',
        'default_hint': 'по умолчанию',

        # Display
        'data_dir':              'Каталог данных',
        'fullscreen':            'Полноэкранный режим',
        'x_resolution':          'Разрешение по горизонтали',
        'y_resolution':          'Разрешение по вертикали',
        'bpp_mode':              'Глубина цвета',
        'capture_mouse':         'Захват мыши в окне',
        'force_window_position': 'Фиксировать окно в позиции (0,0)',
        'view_mode':             'Камера по умолчанию',
        # Controls
        'quit_key':              'Выход из заезда',
        'turn_left_key':         'Поворот влево',
        'turn_right_key':        'Поворот вправо',
        'trick_modifier_key':    'Модификатор трюков',
        'brake_key':             'Торможение',
        'paddle_key':            'Грести / Взмах',
        'jump_key':              'Прыжок',
        'reset_key':             'Сброс позиции',
        'follow_view_key':       'Камера: следование',
        'behind_view_key':       'Камера: сзади',
        'above_view_key':        'Камера: сверху',
        'screenshot_key':        'Снимок экрана',
        'pause_key':             'Пауза',
        # Joystick
        'joystick_paddle_button':   'Кнопка гребли',
        'joystick_brake_button':    'Кнопка тормоза',
        'joystick_jump_button':     'Кнопка прыжка',
        'joystick_trick_button':    'Кнопка трюков',
        'joystick_continue_button': 'Кнопка продолжения',
        'joystick_x_axis':          'Ось X (поворот)',
        'joystick_y_axis':          'Ось Y (гребля/тормоз)',
        # Audio
        'no_audio':           'Полностью отключить звук',
        'sound_enabled':      'Звуковые эффекты',
        'music_enabled':      'Музыка',
        'sound_volume':       'Громкость звука',
        'music_volume':       'Громкость музыки',
        'audio_freq_mode':    'Частота звука',
        'audio_format_mode':  'Бит на сэмпл',
        'audio_stereo':       'Стерео',
        'audio_buffer_size':  'Размер аудио-буфера',
        # Graphics
        'display_fps':                'Показывать FPS',
        'course_detail_level':        'Детализация трассы',
        'forward_clip_distance':      'Дальняя отсечка',
        'backward_clip_distance':     'Задняя отсечка',
        'tree_detail_distance':       'Детализация деревьев',
        'terrain_blending':           'Смешивание текстур',
        'perfect_terrain_blending':   'Точное смешивание',
        'terrain_envmap':             'Блик на льду (envmap)',
        'disable_fog':                'Отключить туман',
        'draw_tux_shadow':            'Тень Tux',
        'tux_sphere_divisions':       'Подразделение сферы Tux',
        'tux_shadow_sphere_divisions':'Подразделение сферы тени',
        'draw_particles':             'Снежные частицы',
        'track_marks':                'Следы на снегу',
        'ui_snow':                    'Снег в интерфейсе',
        'nice_fog':                   'Качественный туман (GL_NICEST)',
        'use_cva':                    'Использовать CVA',
        'cva_hack':                   'Обход CVA (для драйверов)',
        'use_sphere_display_list':    'Список отображения сферы',
        'do_intro_animation':         'Вступительная анимация',
        'mipmap_type':                'Mipmap / фильтр текстур',
        # Advanced
        'ode_solver':           'Решатель ОДУ',
        'fov':                  'Поле зрения (градусы)',
        'debug':                'Флаги отладки',
        'warning_level':        'Уровень предупреждений',
        'write_diagnostic_log': 'Писать diagnostic_log.txt',

        # Enum labels
        'bpp_system':  'Системная',
        'bpp_16':      '16 бит',
        'bpp_32':      '32 бита',
        'view_behind': 'Сзади',
        'view_follow': 'Следование',
        'view_above':  'Сверху',
        'freq_11025':  '11025 Гц',
        'freq_22050':  '22050 Гц',
        'freq_44100':  '44100 Гц',
        'bits_8':  '8 бит',
        'bits_16': '16 бит',
        'mipmap_0': 'GL_NEAREST',
        'mipmap_1': 'GL_LINEAR',
        'mipmap_2': 'NEAREST_MIPMAP_NEAREST',
        'mipmap_3': 'LINEAR_MIPMAP_NEAREST',
        'mipmap_4': 'NEAREST_MIPMAP_LINEAR',
        'mipmap_5': 'LINEAR_MIPMAP_LINEAR',
        'ode_0': 'Модифицированный Эйлер (быстро)',
        'ode_1': 'Рунге-Кутта (2,3)',
        'ode_2': 'Рунге-Кутта (4,5) (точно)',

        # Messages
        'saved':          'Конфигурация успешно сохранена.',
        'save_error':     'Ошибка сохранения файла:',
        'no_file':        'Файл конфигурации не загружен. Нажмите «Обзор...», чтобы выбрать файл.',
        'reset_confirm':  'Сбросить все значения к текущему состоянию файла на диске?',
        'file_not_found': 'Файл не найден:',
        'invalid_value':  'Неверное значение для',
        'unsaved':        'Есть несохранённые изменения. Закрыть всё равно?',
        'key_hint':       'Имена клавиш через пробел, например:  q escape',
    },
}

# ===========================================================================
# Setting definitions
#   kind: bool | int | str | choice
# ===========================================================================
SETTINGS = [
    # --- Display ---
    dict(name='data_dir',              tab='display',  kind='str'),
    dict(name='fullscreen',            tab='display',  kind='bool'),
    dict(name='x_resolution',          tab='display',  kind='int',  lo=320, hi=3840),
    dict(name='y_resolution',          tab='display',  kind='int',  lo=240, hi=2160),
    dict(name='bpp_mode',              tab='display',  kind='choice',
         options=[('0','bpp_system'),('1','bpp_16'),('2','bpp_32')]),
    dict(name='capture_mouse',         tab='display',  kind='bool'),
    dict(name='force_window_position', tab='display',  kind='bool'),
    dict(name='view_mode',             tab='display',  kind='choice',
         options=[('0','view_behind'),('1','view_follow'),('2','view_above')]),

    # --- Controls ---
    dict(name='quit_key',           tab='controls', kind='keys'),
    dict(name='turn_left_key',      tab='controls', kind='keys'),
    dict(name='turn_right_key',     tab='controls', kind='keys'),
    dict(name='trick_modifier_key', tab='controls', kind='keys'),
    dict(name='brake_key',          tab='controls', kind='keys'),
    dict(name='paddle_key',         tab='controls', kind='keys'),
    dict(name='jump_key',           tab='controls', kind='keys'),
    dict(name='reset_key',          tab='controls', kind='keys'),
    dict(name='follow_view_key',    tab='controls', kind='keys'),
    dict(name='behind_view_key',    tab='controls', kind='keys'),
    dict(name='above_view_key',     tab='controls', kind='keys'),
    dict(name='screenshot_key',     tab='controls', kind='keys'),
    dict(name='pause_key',          tab='controls', kind='keys'),

    # --- Joystick ---
    dict(name='joystick_paddle_button',   tab='joystick', kind='int', lo=-1, hi=32),
    dict(name='joystick_brake_button',    tab='joystick', kind='int', lo=-1, hi=32),
    dict(name='joystick_jump_button',     tab='joystick', kind='int', lo=-1, hi=32),
    dict(name='joystick_trick_button',    tab='joystick', kind='int', lo=-1, hi=32),
    dict(name='joystick_continue_button', tab='joystick', kind='int', lo=-1, hi=32),
    dict(name='joystick_x_axis',          tab='joystick', kind='int', lo=0,  hi=16),
    dict(name='joystick_y_axis',          tab='joystick', kind='int', lo=0,  hi=16),

    # --- Audio ---
    dict(name='no_audio',           tab='audio', kind='bool'),
    dict(name='sound_enabled',      tab='audio', kind='bool'),
    dict(name='music_enabled',      tab='audio', kind='bool'),
    dict(name='sound_volume',       tab='audio', kind='int', lo=0, hi=127, slider=True),
    dict(name='music_volume',       tab='audio', kind='int', lo=0, hi=127, slider=True),
    dict(name='audio_freq_mode',    tab='audio', kind='choice',
         options=[('0','freq_11025'),('1','freq_22050'),('2','freq_44100')]),
    dict(name='audio_format_mode',  tab='audio', kind='choice',
         options=[('0','bits_8'),('1','bits_16')]),
    dict(name='audio_stereo',       tab='audio', kind='bool'),
    dict(name='audio_buffer_size',  tab='audio', kind='int', lo=256, hi=65536),

    # --- Graphics ---
    dict(name='display_fps',                tab='graphics', kind='bool'),
    dict(name='course_detail_level',        tab='graphics', kind='int', lo=1, hi=200, slider=True),
    dict(name='forward_clip_distance',      tab='graphics', kind='int', lo=10, hi=500, slider=True),
    dict(name='backward_clip_distance',     tab='graphics', kind='int', lo=0, hi=200),
    dict(name='tree_detail_distance',       tab='graphics', kind='int', lo=0, hi=200),
    dict(name='terrain_blending',           tab='graphics', kind='bool'),
    dict(name='perfect_terrain_blending',   tab='graphics', kind='bool', expert=True),
    dict(name='terrain_envmap',             tab='graphics', kind='bool'),
    dict(name='disable_fog',                tab='graphics', kind='bool'),
    dict(name='draw_tux_shadow',            tab='graphics', kind='bool'),
    dict(name='tux_sphere_divisions',       tab='graphics', kind='int', lo=1, hi=32, expert=True),
    dict(name='tux_shadow_sphere_divisions',tab='graphics', kind='int', lo=1, hi=32, expert=True),
    dict(name='draw_particles',             tab='graphics', kind='bool'),
    dict(name='track_marks',                tab='graphics', kind='bool'),
    dict(name='ui_snow',                    tab='graphics', kind='bool'),
    dict(name='nice_fog',                   tab='graphics', kind='bool', expert=True),
    dict(name='use_cva',                    tab='graphics', kind='bool', expert=True),
    dict(name='cva_hack',                   tab='graphics', kind='bool'),
    dict(name='use_sphere_display_list',    tab='graphics', kind='bool', expert=True),
    dict(name='do_intro_animation',         tab='graphics', kind='bool'),
    dict(name='mipmap_type',                tab='graphics', kind='choice', expert=True,
         options=[('0','mipmap_0'),('1','mipmap_1'),('2','mipmap_2'),
                  ('3','mipmap_3'),('4','mipmap_4'),('5','mipmap_5')]),

    # --- Advanced ---
    dict(name='ode_solver',           tab='advanced', kind='choice',
         options=[('0','ode_0'),('1','ode_1'),('2','ode_2')]),
    dict(name='fov',                  tab='advanced', kind='int', lo=20, hi=120, expert=True),
    dict(name='debug',                tab='advanced', kind='str',  expert=True),
    dict(name='warning_level',        tab='advanced', kind='int', lo=0, hi=100, expert=True),
    dict(name='write_diagnostic_log', tab='advanced', kind='bool'),
]

# Default values (used when a directive is absent from the file)
DEFAULTS = {
    'data_dir':                   '"."',
    'fullscreen':                 'true',
    'x_resolution':               '640',
    'y_resolution':               '480',
    'bpp_mode':                   '0',
    'capture_mouse':              'false',
    'force_window_position':      'false',
    'view_mode':                  '1',
    'quit_key':                   '"q escape"',
    'turn_left_key':              '"j left"',
    'turn_right_key':             '"l right"',
    'trick_modifier_key':         '"d"',
    'brake_key':                  '"k space down"',
    'paddle_key':                 '"i up"',
    'jump_key':                   '"e"',
    'reset_key':                  '"backspace"',
    'follow_view_key':            '"1"',
    'behind_view_key':            '"2"',
    'above_view_key':             '"3"',
    'screenshot_key':             '"="',
    'pause_key':                  '"p"',
    'joystick_paddle_button':     '0',
    'joystick_brake_button':      '2',
    'joystick_jump_button':       '3',
    'joystick_trick_button':      '1',
    'joystick_continue_button':   '0',
    'joystick_x_axis':            '0',
    'joystick_y_axis':            '1',
    'no_audio':                   'false',
    'sound_enabled':              'true',
    'music_enabled':              'true',
    'sound_volume':               '127',
    'music_volume':               '64',
    'audio_freq_mode':            '1',
    'audio_format_mode':          '1',
    'audio_stereo':               'true',
    'audio_buffer_size':          '2048',
    'display_fps':                'false',
    'course_detail_level':        '75',
    'forward_clip_distance':      '75',
    'backward_clip_distance':     '10',
    'tree_detail_distance':       '20',
    'terrain_blending':           'true',
    'perfect_terrain_blending':   'false',
    'terrain_envmap':             'true',
    'disable_fog':                'false',
    'draw_tux_shadow':            'false',
    'tux_sphere_divisions':       '6',
    'tux_shadow_sphere_divisions':'3',
    'draw_particles':             'true',
    'track_marks':                'true',
    'ui_snow':                    'true',
    'nice_fog':                   'true',
    'use_cva':                    'true',
    'cva_hack':                   'true',
    'use_sphere_display_list':    'true',
    'do_intro_animation':         'true',
    'mipmap_type':                '3',
    'ode_solver':                 '1',
    'fov':                        '60',
    'debug':                      '""',
    'warning_level':              '100',
    'write_diagnostic_log':       'false',
}

# Regex that matches a single ``set varname value`` line
SET_RE = re.compile(r'^(\s*set\s+)(\w+)(\s+)(.+?)\s*$')

# ===========================================================================
# Main application class
# ===========================================================================
class TuxRacerSettings:
    TAB_ORDER = ['display', 'controls', 'joystick', 'audio', 'graphics', 'advanced']

    def __init__(self, root):
        self.root = root
        self.lang = 'en'
        # Resolve cross-platform fonts BEFORE any widget is built, so that
        # Cyrillic (and any other non-ASCII) text renders correctly even on
        # systems where the preferred font family is missing.
        _init_fonts(root=root)
        self.filepath = self._find_config_file()
        self.lines = []           # original file lines (mutable)
        self.values = {}          # varname -> raw value string (with quotes if any)
        self.disk_values = {}     # snapshot for "reset" and "unsaved changes" check
        self.vars = {}            # varname -> tk variable
        self.widgets = {}         # varname -> main widget (for state toggling)
        self.row_widgets = {}     # varname -> list of all widgets in the row
        self.snowflakes = []      # animated snow particles
        self._snow_after = None

        self._setup_window()
        self._build_ui()
        # Force an initial gradient draw (the <Configure> event may not have
        # fired yet if the window hasn't been mapped).
        self.root.update_idletasks()
        self._draw_gradient()
        self._start_snow()
        if self.filepath and os.path.isfile(self.filepath):
            self.load_file(self.filepath)
        else:
            # populate UI with defaults so the user can still edit & "Save As"
            self._apply_values_to_ui(dict(DEFAULTS))
            self.disk_values = {}

    # ---- file discovery --------------------------------------------------
    def _find_config_file(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, 'options.txt'),
            os.path.join(script_dir, "config\\", 'options.txt'),
            os.path.join(os.getcwd(), 'options.txt'),
            os.path.join(os.path.expanduser('~'), '.tuxracer', 'options.txt'),
            os.path.join(os.path.expanduser('~'), '.tuxracer-0.61', 'options.txt'),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    # ---- window ----------------------------------------------------------
    def _setup_window(self):
        self.root.title(self.tr('title'))
        self.root.geometry('820x720')
        self.root.minsize(720, 620)
        try:
            self.root.iconbitmap(default='')  # no-op without an icon file
        except Exception:
            pass
        # Full-window gradient background
        self._bg = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self._bg.place(x=0, y=0, relwidth=1, relheight=1)
        self._bg.bind('<Configure>', self._draw_gradient)

    def _draw_gradient(self, _event=None):
        c = self._bg
        c.delete('gradient')
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            return
        # Vertical gradient C_BG_TOP -> C_BG_BOTTOM, drawn as thin rectangles
        steps = max(40, h // 4)
        r1, g1, b1 = self._hex(C_BG_TOP)
        r2, g2, b2 = self._hex(C_BG_BOTTOM)
        for i in range(steps):
            t = i / max(1, steps - 1)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            color = '#%02X%02X%02X' % (r, g, b)
            y0 = i * h // steps
            y1 = (i + 1) * h // steps + 1
            c.create_rectangle(0, y0, w, y1, fill=color, outline='', tags='gradient')
        c.tag_lower('gradient')

    @staticmethod
    def _hex(s):
        s = s.lstrip('#')
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)

    # ---- UI scaffolding --------------------------------------------------
    def _build_ui(self):
        # Header (snow canvas + title)
        self.header = tk.Frame(self.root, bg=C_BG_TOP, height=110)
        self.header.pack(fill='x', side='top')
        self.header.pack_propagate(False)

        self.snow_canvas = tk.Canvas(self.header, bg=C_BG_TOP,
                                     highlightthickness=0, bd=0)
        self.snow_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._snow_realized = False
        self._snow_prev_size = (1, 1)
        self.snow_canvas.bind('<Configure>', self._on_snow_canvas_resize)

        # Title block
        title_frame = tk.Frame(self.header, bg=C_BG_TOP)
        title_frame.place(x=24, y=18)
        self.title_lbl = tk.Label(title_frame, text=self.tr('title'),
                                  bg=C_BG_TOP, fg=C_HEADER,
                                  font=F(22, bold=True))
        self.title_lbl.pack(anchor='w')
        self.subt_lbl = tk.Label(title_frame, text=self.tr('subtitle'),
                                 bg=C_BG_TOP, fg=C_TEXT_SOFT,
                                 font=F(11, italic=True))
        self.subt_lbl.pack(anchor='w')

        # Language selector
        lang_frame = tk.Frame(self.header, bg=C_BG_TOP)
        lang_frame.place(relx=1.0, x=-24, y=24, anchor='ne')
        tk.Label(lang_frame, text=self.tr('lang'), bg=C_BG_TOP,
                 fg=C_TEXT_SOFT, font=F(10)).pack(side='left', padx=(0, 6))
        self.lang_var = tk.StringVar(value=self.lang)
        for code, label in (('en', 'EN  English'), ('ru', 'RU  Русский')):
            rb = tk.Radiobutton(lang_frame, text=label, variable=self.lang_var,
                                value=code, bg=C_BG_TOP, fg=C_TEXT,
                                activebackground=C_BG_TOP, activeforeground=C_ACCENT,
                                selectcolor=C_BG_TOP, font=F(10),
                                command=self._switch_language)
            rb.pack(side='left', padx=4)

        # File bar
        self.filebar = tk.Frame(self.root, bg=C_SNOW, height=44)
        self.filebar.pack(fill='x', side='top')
        self.filebar.pack_propagate(False)
        tk.Label(self.filebar, text=self.tr('file_label'), bg=C_SNOW,
                 fg=C_TEXT, font=F(10, bold=True)).pack(side='left', padx=(16, 6), pady=10)
        self.file_var = tk.StringVar(value=self.filepath or '')
        self.file_entry = tk.Entry(self.filebar, textvariable=self.file_var,
                                   bg=C_PANEL, fg=C_TEXT,
                                   readonlybackground=C_PANEL,
                                   relief='flat', bd=0,
                                   font=FM(10))
        self.file_entry.pack(side='left', fill='x', expand=True, padx=(0, 8), pady=10)
        self.file_entry.configure(state='readonly')

        self.btn_browse = self._make_button(self.filebar, self.tr('browse'), self._on_browse, small=True)
        self.btn_browse.pack(side='left', padx=3, pady=8)
        self.btn_new = self._make_button(self.filebar, self.tr('new_file'), self._on_new, small=True)
        self.btn_new.pack(side='left', padx=3, pady=8)

        # Notebook (tabs) using a custom-styled ttk.Notebook
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TNotebook', background=C_BG_BOTTOM, borderwidth=0)
        style.configure('TNotebook.Tab',
                        background=C_TAB_BG, foreground=C_TEXT_SOFT,
                        padding=(18, 8), font=F(10, bold=True),
                        borderwidth=0)
        style.map('TNotebook.Tab',
                  background=[('selected', C_TAB_ACTIVE)],
                  foreground=[('selected', C_ACCENT_DARK)],
                  expand=[('selected', (1, 1, 1, 0))])

        self.notebook = ttk.Notebook(self.root, style='TNotebook')
        self.notebook.pack(fill='both', expand=True, padx=16, pady=(8, 4))

        self.tabs = {}
        self.tab_scrolls = {}
        for tab in self.TAB_ORDER:
            outer = tk.Frame(self.notebook, bg=C_PANEL,
                             highlightbackground=C_TAB_BORDER,
                             highlightthickness=1, bd=0)
            self.notebook.add(outer, text=self._tab_label(tab))
            self.tabs[tab] = outer
            self._build_tab(outer, tab)

        # Footer
        self.footer = tk.Frame(self.root, bg=C_SNOW, height=58)
        self.footer.pack(fill='x', side='bottom')
        self.footer.pack_propagate(False)
        self.btn_save    = self._make_button(self.footer, self.tr('save'),    self._on_save)
        self.btn_save_as = self._make_button(self.footer, self.tr('save_as'), self._on_save_as)
        self.btn_reset   = self._make_button(self.footer, self.tr('reset'),   self._on_reset, secondary=True)
        self.btn_close   = self._make_button(self.footer, self.tr('close'),   self._on_close, secondary=True)
        self.btn_save   .pack(side='right', padx=4, pady=12)
        self.btn_save_as.pack(side='right', padx=4, pady=12)
        self.btn_close  .pack(side='left', padx=4, pady=12)
        self.btn_reset  .pack(side='left', padx=4, pady=12)

        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _make_button(self, parent, text, command, small=False, secondary=False):
        bg = C_PANEL if secondary else C_ACCENT
        fg = C_ACCENT_DARK if secondary else C_TEXT_LIGHT
        bd_color = C_ACCENT if secondary else C_ACCENT
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=fg, activebackground=C_ACCENT_HOVER,
                        activeforeground=C_TEXT_LIGHT,
                        relief='flat', bd=0, cursor='hand2',
                        font=F(10, bold=True),
                        padx=14 if small else 18,
                        pady=4 if small else 6,
                        highlightbackground=bd_color,
                        highlightthickness=1,
                        disabledforeground=C_DISABLED)
        # hover effect
        def on_enter(_e):
            if btn['state'] == 'normal':
                btn.configure(bg=C_ACCENT_HOVER if not secondary else C_TAB_BG)
        def on_leave(_e):
            if btn['state'] == 'normal':
                btn.configure(bg=bg)
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        return btn

    # ---- tab building ----------------------------------------------------
    def _build_tab(self, outer, tab):
        # Scrollable inner frame
        canvas = tk.Canvas(outer, bg=C_PANEL, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient='vertical', command=canvas.yview,
                                 bg=C_SNOW, troughcolor=C_SNOW,
                                 highlightthickness=0, bd=0,
                                 activebackground=C_ACCENT)
        scroll_frame = tk.Frame(canvas, bg=C_PANEL)
        scroll_frame.bind('<Configure>',
                          lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.tab_scrolls[tab] = (canvas, scroll_frame)

        # Mouse-wheel scrolling
        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
        canvas.bind('<Enter>', lambda _e: canvas.bind_all('<MouseWheel>', _wheel))
        canvas.bind('<Leave>', lambda _e: canvas.unbind_all('<MouseWheel>'))

        rows = [s for s in SETTINGS if s['tab'] == tab]
        for i, sdef in enumerate(rows):
            self._build_row(scroll_frame, sdef, i)

    def _build_row(self, parent, sdef, row):
        name = sdef['name']
        kind = sdef['kind']
        expert = sdef.get('expert', False)
        label_text = self.tr(name)
        if expert:
            label_text += '  ' + self.tr('expert')

        # Container row
        rowframe = tk.Frame(parent, bg=C_PANEL)
        rowframe.grid(row=row, column=0, sticky='ew', padx=18, pady=5)
        parent.grid_columnconfigure(0, weight=1)
        # Thin bottom border via separator
        sep = tk.Frame(rowframe, bg=C_PANEL_BORDER, height=1)
        sep.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(5, 0))

        # Label
        lbl = tk.Label(rowframe, text=label_text, bg=C_PANEL, fg=C_TEXT,
                       font=F(10, bold=True), anchor='w', justify='left')
        lbl.grid(row=0, column=0, sticky='w', padx=(0, 10))

        # Hint (range / default)
        hint_parts = []
        if kind == 'int' and 'lo' in sdef:
            hint_parts.append('%s %d..%d' % (self.tr('range_hint'), sdef['lo'], sdef['hi']))
        if name in DEFAULTS:
            d = DEFAULTS[name].strip('"')
            hint_parts.append('%s: %s' % (self.tr('default_hint'), d))
        hint = tk.Label(rowframe, text='   '.join(hint_parts), bg=C_PANEL,
                        fg=C_TEXT_SOFT, font=F(8, italic=True))
        hint.grid(row=0, column=1, sticky='w')

        # Widget container
        wframe = tk.Frame(rowframe, bg=C_PANEL)
        wframe.grid(row=0, column=2, sticky='e', padx=(10, 0))
        rowframe.grid_columnconfigure(2, weight=1)
        rowframe.grid_columnconfigure(1, weight=1)

        var = None
        widget = None
        if kind == 'bool':
            var = tk.BooleanVar()
            widget = tk.Checkbutton(wframe, variable=var, bg=C_PANEL,
                                    activebackground=C_PANEL, selectcolor=C_SNOW,
                                    bd=0, cursor='hand2',
                                    highlightthickness=0)
            widget.pack(side='right')
        elif kind == 'int':
            var = tk.StringVar()
            if sdef.get('slider'):
                slider = tk.Scale(wframe, from_=sdef['lo'], to=sdef['hi'],
                                  orient='horizontal', variable=var,
                                  bg=C_PANEL, fg=C_TEXT, troughcolor=C_SNOW,
                                  highlightthickness=0, bd=0,
                                  activebackground=C_ACCENT,
                                  font=F(8),
                                  length=220, showvalue=True,
                                  resolution=1)
                slider.pack(side='right')
                # keep entry too for direct edit
                ent = tk.Entry(wframe, textvariable=var, width=6,
                               bg=C_SNOW, fg=C_TEXT, relief='flat',
                               font=FM(10), justify='right',
                               highlightbackground=C_PANEL_BORDER,
                               highlightthickness=1)
                ent.pack(side='right', padx=(0, 6))
                widget = ent
            else:
                ent = tk.Entry(wframe, textvariable=var, width=10,
                               bg=C_SNOW, fg=C_TEXT, relief='flat',
                               font=FM(10), justify='right',
                               highlightbackground=C_PANEL_BORDER,
                               highlightthickness=1)
                ent.pack(side='right')
                widget = ent
        elif kind == 'choice':
            var = tk.StringVar()
            # Build human-readable option list
            options = []
            value_to_label = {}
            for val, key in sdef['options']:
                label = self.tr(key)
                options.append('%s  —  %s' % (val, label))
                value_to_label['%s  —  %s' % (val, label)] = val
            cb = ttk.Combobox(wframe, textvariable=var, values=options,
                              state='readonly', width=24, font=F(10))
            cb.pack(side='right')
            cb._value_to_label = value_to_label  # type: ignore[attr-defined]
            cb._label_to_value = {v: k for k, v in value_to_label.items()}   # type: ignore[attr-defined]
            cb._raw_options = sdef['options']                                 # type: ignore[attr-defined]
            widget = cb
        elif kind == 'keys':
            var = tk.StringVar()
            ent = tk.Entry(wframe, textvariable=var, width=22,
                           bg=C_SNOW, fg=C_TEXT, relief='flat',
                           font=FM(10), justify='right',
                           highlightbackground=C_PANEL_BORDER,
                           highlightthickness=1)
            ent.pack(side='right')
            tk.Label(wframe, text=self.tr('key_hint'), bg=C_PANEL,
                     fg=C_TEXT_SOFT, font=F(8, italic=True)).pack(side='right', padx=(0, 6))
            widget = ent
        else:  # str
            var = tk.StringVar()
            ent = tk.Entry(wframe, textvariable=var, width=24,
                           bg=C_SNOW, fg=C_TEXT, relief='flat',
                           font=FM(10), justify='right',
                           highlightbackground=C_PANEL_BORDER,
                           highlightthickness=1)
            ent.pack(side='right')
            widget = ent

        self.vars[name] = var
        self.widgets[name] = widget
        self.row_widgets[name] = [rowframe, lbl, hint, wframe]

    # ---- snow animation --------------------------------------------------
    def _on_snow_canvas_resize(self, _event=None):
        # When the canvas first gets a real size, (re)seed all flakes across it.
        w = max(1, self.snow_canvas.winfo_width())
        h = max(1, self.snow_canvas.winfo_height())
        if w <= 1 or h <= 1:
            return
        if (not self._snow_realized) or (abs(w - self._snow_prev_size[0]) > 50):
            self._snow_realized = True
            self.snowflakes = []
            for _ in range(55):
                self.snowflakes.append(self._new_flake(initial=True))
        self._snow_prev_size = (w, h)

    def _start_snow(self):
        self.snowflakes = []
        # Try to seed now; if canvas isn't realized yet, the <Configure>
        # binding will do it as soon as the canvas has a real size.
        w = max(1, self.snow_canvas.winfo_width())
        h = max(1, self.snow_canvas.winfo_height())
        if w > 1 and h > 1:
            self._snow_realized = True
            self._snow_prev_size = (w, h)
            for _ in range(55):
                self.snowflakes.append(self._new_flake(initial=True))
        self._snow_step()

    def _new_flake(self, initial=False):
        w = max(80, self.snow_canvas.winfo_width())
        h = max(80, self.snow_canvas.winfo_height())
        r = random.uniform(1.6, 3.8)
        return {
            'x': random.uniform(0, w),
            'y': random.uniform(0, h) if initial else -r,
            'r': r,
            'vy': random.uniform(0.35, 1.2) * (r / 2.0),
            'drift': random.uniform(-0.35, 0.35),
            'phase': random.uniform(0, 2 * math.pi),
        }

    def _snow_step(self):
        c = self.snow_canvas
        c.delete('snow')
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        if w <= 1 or h <= 1:
            self._snow_after = self.root.after(80, self._snow_step)
            return
        for f in self.snowflakes:
            f['y'] += f['vy']
            f['phase'] += 0.05
            x = f['x'] + math.sin(f['phase']) * 6 * f['drift']
            if f['y'] - f['r'] > h:
                nf = self._new_flake()
                f.update(nf)
                x = f['x'] + math.sin(f['phase']) * 6 * f['drift']
            # also respawn if drifted off the sides
            if x < -10 or x > w + 10:
                f['x'] = random.uniform(0, w)
                x = f['x']
            c.create_oval(x - f['r'], f['y'] - f['r'],
                          x + f['r'], f['y'] + f['r'],
                          fill=C_SNOWFLAKE, outline=C_SNOWFLAKE_OUT,
                          width=1.0, tags='snow')
        self._snow_after = self.root.after(45, self._snow_step)

    # ---- file IO ---------------------------------------------------------
    def load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                self.lines = fh.read().splitlines()
        except OSError as e:
            messagebox.showerror(self.tr('title'),
                                 '%s\n%s' % (self.tr('file_not_found'), e))
            return
        self.filepath = path
        self.file_var.set(path)
        self.values = self._parse_values(self.lines)
        self.disk_values = dict(self.values)
        self._apply_values_to_ui(self.values)

    def _parse_values(self, lines):
        out = {}
        for line in lines:
            m = SET_RE.match(line)
            if m:
                out[m.group(2)] = m.group(4).strip()
        return out

    def _apply_values_to_ui(self, values):
        for sdef in SETTINGS:
            name = sdef['name']
            raw = values.get(name, DEFAULTS.get(name, ''))
            self._set_widget(name, raw)

    def _set_widget(self, name, raw):
        sdef = next(s for s in SETTINGS if s['name'] == name)
        kind = sdef['kind']
        var = self.vars[name]
        if kind == 'bool':
            val = raw.strip().lower() in ('1', 'true', 'yes', 'on')
            var.set(bool(val))
        elif kind == 'choice':
            # raw may be '0', '1', etc. — convert to label
            key = None
            for v, k in sdef['options']:
                if v == raw.strip():
                    key = k
                    break
            if key is None:
                key = sdef['options'][0][1]
            label = self.tr(key)
            display = '%s  —  %s' % (raw.strip() or sdef['options'][0][0], label)
            var.set(display)
        elif kind == 'int':
            # strip quotes if any
            v = raw.strip().strip('"')
            try:
                int(v)
            except ValueError:
                v = DEFAULTS.get(name, '0').strip('"')
            var.set(v)
        else:  # str / keys — strip surrounding quotes for display
            v = raw.strip()
            if v.startswith('"') and v.endswith('"') and len(v) >= 2:
                v = v[1:-1]
            var.set(v)

    def _read_widget(self, name):
        sdef = next(s for s in SETTINGS if s['name'] == name)
        kind = sdef['kind']
        var = self.vars[name]
        if kind == 'bool':
            return 'true' if var.get() else 'false'
        if kind == 'choice':
            display = var.get()
            # Try to map back to value via current language label
            for v, k in sdef['options']:
                label = self.tr(k)
                if display == '%s  —  %s' % (v, label):
                    return v
            # Fall back: maybe language changed; try matching against all langs
            for v, k in sdef['options']:
                for lang in L:
                    label = L[lang].get(k, k)
                    if display == '%s  —  %s' % (v, label):
                        return v
            # Last resort: take the leading token
            tok = display.split(' ', 1)[0] if display else sdef['options'][0][0]
            return tok
        if kind == 'int':
            v = var.get().strip()
            try:
                n = int(v)
            except ValueError:
                raise ValueError(name)
            if 'lo' in sdef:
                n = max(sdef['lo'], min(sdef['hi'], n))
            return str(n)
        # str / keys: user typed without quotes; add them back on save
        v = var.get().strip()
        if kind in ('keys', 'str'):
            if not (v.startswith('"') and v.endswith('"') and len(v) >= 2):
                v = '"%s"' % v
        return v

    # ---- actions ---------------------------------------------------------
    def _on_browse(self):
        path = filedialog.askopenfilename(
            title=self.tr('browse'),
            filetypes=[('Tux Racer options', '*.txt'),
                       ('All files', '*.*')],
            initialdir=os.path.dirname(self.filepath) or os.getcwd())
        if path:
            self.load_file(path)

    def _on_new(self):
        path = filedialog.asksaveasfilename(
            title=self.tr('new_file'),
            defaultextension='.txt',
            filetypes=[('Tux Racer options', '*.txt'),
                       ('All files', '*.*')],
            initialfile='options.txt')
        if not path:
            return
        # Start from a fresh DEFAULTS-based file
        self.lines = ['# Tux Racer 0.61 configuration file', '#']
        self.values = dict(DEFAULTS)
        self.disk_values = {}
        self.filepath = path
        self.file_var.set(path)
        self._apply_values_to_ui(self.values)
        self._write_file(path)

    def _on_save(self):
        if not self.filepath:
            messagebox.showwarning(self.tr('title'), self.tr('no_file'))
            return
        self._write_file(self.filepath)

    def _on_save_as(self):
        path = filedialog.asksaveasfilename(
            title=self.tr('save_as'),
            defaultextension='.txt',
            filetypes=[('Tux Racer options', '*.txt'),
                       ('All files', '*.*')],
            initialdir=os.path.dirname(self.filepath) or os.getcwd(),
            initialfile=os.path.basename(self.filepath) if self.filepath else 'options.txt')
        if path:
            self._write_file(path)

    def _write_file(self, path):
        # Build new values from UI
        new_values = {}
        errors = []
        for sdef in SETTINGS:
            name = sdef['name']
            try:
                new_values[name] = self._read_widget(name)
            except ValueError:
                errors.append(name)
        if errors:
            messagebox.showerror(self.tr('title'),
                                 '%s: %s' % (self.tr('invalid_value'),
                                             ', '.join(errors)))
            return

        # Update existing lines in place
        seen = set()
        for i, line in enumerate(self.lines):
            m = SET_RE.match(line)
            if m and m.group(2) in new_values:
                varname = m.group(2)
                self.lines[i] = '%s%s%s%s' % (m.group(1), varname, m.group(3), new_values[varname])
                seen.add(varname)

        # Append missing directives at the end
        missing = [s['name'] for s in SETTINGS if s['name'] not in seen]
        if missing:
            if self.lines and self.lines[-1].strip() != '':
                self.lines.append('')
            self.lines.append('# --- directives added by tuxracersettings.pyw ---')
            for name in missing:
                self.lines.append('set %s %s' % (name, new_values[name]))

        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('\n'.join(self.lines) + '\n')
        except OSError as e:
            messagebox.showerror(self.tr('title'),
                                 '%s\n%s' % (self.tr('save_error'), e))
            return

        self.filepath = path
        self.file_var.set(path)
        self.values = new_values
        self.disk_values = dict(new_values)
        messagebox.showinfo(self.tr('title'), self.tr('saved'))

    def _on_reset(self):
        if not self.disk_values and not self.filepath:
            self._apply_values_to_ui(dict(DEFAULTS))
            return
        if messagebox.askyesno(self.tr('title'), self.tr('reset_confirm')):
            self._apply_values_to_ui(self.disk_values or dict(DEFAULTS))

    def _on_close(self):
        if self._is_dirty():
            if not messagebox.askyesno(self.tr('title'), self.tr('unsaved')):
                return
        if self._snow_after is not None:
            self.root.after_cancel(self._snow_after)
        self.root.destroy()

    def _is_dirty(self):
        for sdef in SETTINGS:
            name = sdef['name']
            try:
                cur = self._read_widget(name)
            except ValueError:
                return True
            disk = self.disk_values.get(name, DEFAULTS.get(name, ''))
            if cur != disk:
                return True
        return False

    # ---- language --------------------------------------------------------
    def tr(self, key):
        return L[self.lang].get(key, key)

    def _tab_label(self, tab):
        return self.tr('tab_' + tab)

    def _switch_language(self):
        new_lang = self.lang_var.get()
        if new_lang == self.lang:
            return
        # Snapshot current UI values BEFORE rebuilding widgets
        snapshot = {}
        for sdef in SETTINGS:
            name = sdef['name']
            try:
                snapshot[name] = self._read_widget(name)
            except ValueError:
                snapshot[name] = DEFAULTS.get(name, '')
        self.lang = new_lang

        # Update static labels
        self.root.title(self.tr('title'))
        self.title_lbl.configure(text=self.tr('title'))
        self.subt_lbl.configure(text=self.tr('subtitle'))
        self.btn_save   .configure(text=self.tr('save'))
        self.btn_save_as.configure(text=self.tr('save_as'))
        self.btn_reset  .configure(text=self.tr('reset'))
        self.btn_close  .configure(text=self.tr('close'))
        self.btn_browse .configure(text=self.tr('browse'))
        self.btn_new    .configure(text=self.tr('new_file'))

        # Update tab labels
        for i, tab in enumerate(self.TAB_ORDER):
            self.notebook.tab(i, text=self._tab_label(tab))

        # Update file label
        for child in self.filebar.winfo_children():
            if isinstance(child, tk.Label) and child['text'] != self.tr('file_label') \
                    and child['text'] in (L['en']['file_label'], L['ru']['file_label']):
                child.configure(text=self.tr('file_label'))
            elif isinstance(child, tk.Label) and child['text'] in (L['en']['file_label'], L['ru']['file_label']):
                child.configure(text=self.tr('file_label'))

        # Rebuild row labels & hints
        for sdef in SETTINGS:
            name = sdef['name']
            rowframe, lbl, hint, wframe = self.row_widgets[name]
            expert = sdef.get('expert', False)
            text = self.tr(name)
            if expert:
                text += '  ' + self.tr('expert')
            lbl.configure(text=text)
            # Rebuild hint
            hint_parts = []
            if sdef['kind'] == 'int' and 'lo' in sdef:
                hint_parts.append('%s %d..%d' % (self.tr('range_hint'), sdef['lo'], sdef['hi']))
            if name in DEFAULTS:
                d = DEFAULTS[name].strip('"')
                hint_parts.append('%s: %s' % (self.tr('default_hint'), d))
            hint.configure(text='   '.join(hint_parts))

            # For choice widgets we need to rebuild the option list and re-set value
            if sdef['kind'] == 'choice':
                cb = self.widgets[name]
                options = []
                for val, key in sdef['options']:
                    options.append('%s  —  %s' % (val, self.tr(key)))
                cb.configure(values=options)
                # Re-set display value from snapshot
                for v, k in sdef['options']:
                    if v == snapshot[name]:
                        cb.set('%s  —  %s' % (v, self.tr(k)))
                        break
            else:
                # Restore value as-is
                self._set_widget(name, snapshot[name])

        # Update key hint labels
        for sdef in SETTINGS:
            if sdef['kind'] != 'keys':
                continue
            wframe = self.row_widgets[sdef['name']][3]
            for child in wframe.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(text=self.tr('key_hint'))

    # ---- language radio button re-label on switch ------------------------
    def _refresh_lang_radios(self):
        # not strictly needed because labels are static, but kept for clarity
        pass


# ===========================================================================
# Entry point
# ===========================================================================
def main():
    root = tk.Tk()
    app = TuxRacerSettings(root)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # pragma: no cover
        # .pyw hides console — surface errors in a messagebox if possible
        try:
            from tkinter import messagebox as _mb
            _mb.showerror('Tux Racer Settings', str(exc))
        except Exception:
            pass
        raise
