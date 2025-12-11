DESIGN = """
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #ff00ff, stop:0.25 #ffff00,
                                stop:0.5 #00ffff, stop:0.75 #00ff00,
                                stop:1 #ff0000);
    color: #000000;
    font-family: "Comic Sans MS";
    font-size: 18px;
    font-weight: bold;
    border: 5px dashed magenta;
    border-radius: 20px;
    padding: 10px;
}

QPushButton {
    background-color: qconicalgradient(cx:0.5, cy:0.5, angle:90,
                                       stop:0 red, stop:0.25 yellow,
                                       stop:0.5 lime, stop:0.75 cyan,
                                       stop:1 magenta);
    color: black;
    border: 3px dotted hotpink;
    border-radius: 10px;
    padding: 6px;
}

QPushButton:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                      fx:0.3, fy:0.3,
                                      stop:0 white, stop:1 red);
    transform: rotate(10deg);
}

QScrollBar:vertical {
    background: repeating-linear-gradient(
        to bottom,
        lime,
        yellow 10px,
        hotpink 20px
    );
    width: 20px;
    border: 2px solid magenta;
    border-radius: 10px;
}

QScrollBar::handle:vertical {
    background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                stop:0 white, stop:1 blue);
    border: 2px solid yellow;
    border-radius: 8px;
}

QScrollBar::handle:vertical:hover {
    background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                stop:0 cyan, stop:1 red);
}

QHeaderView::section {
    background-color: #ff69b4;
    color: #000;
    border: 2px solid black;
    font-weight: bold;
    padding: 4px;
    text-transform: uppercase;
}
"""

DESIGN_2 = """
QWidget {
    background: qconicalgradient(cx:0.5, cy:0.5, angle:0,
                                 stop:0 #00ffff,
                                 stop:0.25 #ff00ff,
                                 stop:0.5 #ffff00,
                                 stop:0.75 #00ff00,
                                 stop:1 #00ffff);
    color: black;
    font-family: "Papyrus";
    font-size: 20px;
    font-weight: 900;
    border: 6px double hotpink;
    border-radius: 30px;
    padding: 15px;
    text-shadow: 2px 2px 5px #ff00ff;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #ff007f, stop:1 #00ffff);
    color: white;
    border: 3px solid yellow;
    border-radius: 12px;
    padding: 10px;
    font-size: 16px;
    text-transform: uppercase;
}

QPushButton:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                      fx:0.3, fy:0.3,
                                      stop:0 #ffffff, stop:1 #ff0000);
    color: black;
    border: 3px dotted cyan;
}

QLineEdit {
    background-color: rgba(0, 0, 0, 0.7);
    color: #00ffcc;
    border: 2px solid #ff00ff;
    border-radius: 8px;
    padding: 6px;
}

QScrollBar:vertical {
    background: repeating-linear-gradient(
        to bottom,
        #00ffff, #ff00ff 10px, #ffff00 20px
    );
    width: 22px;
    border-radius: 10px;
}
"""

DESIGN_3 = """
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #ffb6c1, stop:0.25 #fffacd,
                                stop:0.5 #b0e0e6, stop:0.75 #dda0dd,
                                stop:1 #98fb98);
    color: #4b0082;
    font-family: "Comic Sans MS";
    font-size: 18px;
    border: 8px ridge pink;
    border-radius: 25px;
    padding: 15px;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #fff0f5, stop:1 #ff69b4);
    border: 3px solid hotpink;
    border-radius: 15px;
    color: purple;
    font-weight: bold;
    padding: 10px;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #ff69b4, stop:1 #fff0f5);
    border: 3px dashed magenta;
    color: white;
}

QLabel {
    background-color: transparent;
    color: #4b0082;
    text-decoration: underline wavy hotpink;
}

QScrollBar:vertical {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffe4e1, stop:1 #ffb6c1);
    border: 2px solid pink;
    border-radius: 10px;
    width: 20px;
}

QScrollBar::handle:vertical {
    background: #ff69b4;
    border: 2px solid #ffb6c1;
    border-radius: 8px;
}
"""

DESIGN_4 = """
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
    color: #e0b0ff;
    font-family: "Lucida Console";
    font-size: 16px;
    border: 3px groove magenta;
    border-radius: 15px;
    padding: 10px;
    selection-background-color: #ff00ff;
    selection-color: black;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #8e2de2, stop:1 #4a00e0);
    color: #f5f5f5;
    border: 2px solid #ff00ff;
    border-radius: 12px;
    padding: 8px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                      stop:0 #ff00ff, stop:1 #4a00e0);
    color: black;
    border: 3px dotted #00ffff;
}

QLineEdit {
    background-color: rgba(0, 0, 0, 0.7);
    color: #00ffff;
    border: 2px solid #ff00ff;
    border-radius: 8px;
    padding: 5px;
}

QScrollBar:vertical {
    background: #1a1a1a;
    border: 2px solid #ff00ff;
    width: 20px;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #ff00ff, stop:1 #00ffff);
    border-radius: 8px;
}
"""

DESIGN_5 = """
QWidget {
    background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                                fx:0.3, fy:0.3,
                                stop:0 #e6e6fa, stop:1 #9370db);
    color: navy;
    font-family: "Times New Roman";
    font-style: italic;
    font-size: 17px;
    border: 5px outset gold;
    border-radius: 25px;
}

QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #fffacd, stop:1 #dda0dd);
    border: 3px groove purple;
    border-radius: 15px;
    color: darkblue;
    font-weight: bold;
    padding: 8px;
}

QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                      stop:0 #9370db, stop:1 #fffacd);
    border: 3px double gold;
}

QLabel {
    background: transparent;
    color: midnightblue;
    text-decoration: overline underline wavy gold;
}
"""