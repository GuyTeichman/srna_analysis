# -*- coding: utf-8 -*-
import sys
import warnings

__all__ = ['general', 'filtering', 'enrichment', '__attr_file_key__', '__biotype_file_key__', '__font_key__',
           '__font_size_key__', '__stylesheet_key__', '__show_tutorial_key__', '__databases_key__', "FROZEN_ENV"]
__name__ = "rnalysis"
__author__ = "Guy Teichman"
__email__ = "guyteichman@gmail.com"
__version__ = "4.1.1"
__license__ = "MIT"
__attr_file_key__ = "attribute_reference_table"
__biotype_file_key__ = "biotype_reference_table"
__font_key__ = "gui_font"
__font_size_key__ = "gui_font_size"
__stylesheet_key__ = "gui_stylesheet"
__show_tutorial_key__ = "show_tutorial_on_startup"
__report_gen_key__ = "ask_report_generation"
__databases_key__ = "databases"
FROZEN_ENV = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def _simple_warning_format(msg, *args, **kwargs):
    # ignore everything except the warning message
    return f"Warning: {msg}\n"


warnings.formatwarning = _simple_warning_format
warnings.simplefilter('always', UserWarning)
warnings.filterwarnings('ignore', message='.*layout not applied.*')
