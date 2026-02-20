"""
Keyboard Navigation Enhancement for NovelTrad.
Adds arrow key navigation between segments and improved keyboard shortcuts.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QShortcut
from PyQt6.QtGui import QKeySequence


def setup_keyboard_navigation(main_window):
    """
    Setup enhanced keyboard navigation for the main window.
    
    Features:
    - Arrow Up/Down: Navigate between segments
    - Ctrl+Arrow: Jump 10 segments at a time
    - Home/End: Jump to first/last segment
    - Ctrl+G: Go to segment dialog
    """
    
    # Navigate to next segment
    next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), main_window)
    next_shortcut.activated.connect(lambda: navigate_segment(main_window, 1))
    
    # Navigate to previous segment
    prev_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), main_window)
    prev_shortcut.activated.connect(lambda: navigate_segment(main_window, -1))
    
    # Jump 10 segments forward
    next_10_shortcut = QShortcut(QKeySequence("Ctrl+Down"), main_window)
    next_10_shortcut.activated.connect(lambda: navigate_segment(main_window, 10))
    
    # Jump 10 segments backward
    prev_10_shortcut = QShortcut(QKeySequence("Ctrl+Up"), main_window)
    prev_10_shortcut.activated.connect(lambda: navigate_segment(main_window, -10))
    
    # Jump to first segment
    first_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Home), main_window)
    first_shortcut.activated.connect(lambda: jump_to_segment(main_window, 0))
    
    # Jump to last segment
    last_shortcut = QShortcut(QKeySequence(Qt.Key.Key_End), main_window)
    last_shortcut.activated.connect(lambda: jump_to_last_segment(main_window))
    
    return {
        'next': next_shortcut,
        'prev': prev_shortcut,
        'next_10': next_10_shortcut,
        'prev_10': prev_10_shortcut,
        'first': first_shortcut,
        'last': last_shortcut,
    }


def navigate_segment(main_window, direction):
    """
    Navigate to next/previous segment.
    
    Args:
        main_window: MainWindow instance
        direction: +1 for next, -1 for previous (or multiples of 10 for Ctrl+arrows)
    """
    if not hasattr(main_window, 'segment_list') or not main_window.segment_list:
        return
    
    current = main_window.current_segment_index
    new_index = current + direction
    
    # Clamp to valid range
    max_index = len(main_window.segment_list) - 1
    new_index = max(0, min(new_index, max_index))
    
    # Update current segment
    main_window.current_segment_index = new_index
    
    # Update UI
    if hasattr(main_window, 'segment_scroll'):
        # Scroll to make segment visible
        main_window.segment_scroll.verticalScrollBar().setValue(
            new_index * main_window.segment_list[0].height()
        )
    
    # Update selection highlight
    main_window.update_segment_selection(new_index)


def jump_to_segment(main_window, index):
    """Jump to a specific segment index."""
    if not hasattr(main_window, 'segment_list') or not main_window.segment_list:
        return
    
    max_index = len(main_window.segment_list) - 1
    index = max(0, min(index, max_index))
    
    main_window.current_segment_index = index
    
    if hasattr(main_window, 'segment_scroll'):
        main_window.segment_scroll.verticalScrollBar().setValue(
            index * main_window.segment_list[0].height()
        )
    
    main_window.update_segment_selection(index)


def jump_to_last_segment(main_window):
    """Jump to the last segment."""
    if not hasattr(main_window, 'segment_list') or not main_window.segment_list:
        return
    
    jump_to_segment(main_window, len(main_window.segment_list) - 1)


def show_go_to_segment_dialog(main_window):
    """
    Show a dialog to jump to a specific segment number.
    """
    from PyQt6.QtWidgets import QInputDialog, QLineEdit
    
    if not hasattr(main_window, 'segment_list') or not main_window.segment_list:
        return
    
    total = len(main_window.segment_list)
    
    segment_num, ok = QInputDialog.getInt(
        main_window,
        "Go to Segment",
        f"Segment number (1-{total}):",
        main_window.current_segment_index + 1,
        1,
        total
    )
    
    if ok:
        jump_to_segment(main_window, segment_num - 1)
