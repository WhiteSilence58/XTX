Modularisierte Version von main.py.

Dateien:
- main.py: Bootstrap-Datei, lädt alle Module in definierter Reihenfolge
- modules/*.py: thematisch getrennte Bereiche

Hinweis:
Diese Variante hält die Änderungen bewusst klein. Die Module werden zur Laufzeit in denselben globalen Namespace geladen, damit bestehende Querverweise erhalten bleiben.
