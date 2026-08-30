# QNEST print pieces

Three print items built on the same theme as the website: same palette, same Arial-only type rules,
same numbered workflow rail.

| File | What it is | Paper |
|---|---|---|
| `brochure.html` | 4-panel brochure, folded once | 2 × A4 landscape, double-sided |
| `handout.html` | One-page leave-behind | 1 × A4 portrait, single-sided |
| `card.html` | Business card, front and back | 85 × 55 mm + 3 mm bleed |

A ready-made PDF sits next to each one.

## Editing

Open the `.html` file in any text editor and change the words. That's the whole job — the text is
plain HTML in reading order, with comments marking each panel.

Colour, type size and spacing live in `print.css`, shared by all three. Change a value there and every
piece follows. The variables at the top of that file are the palette:

```css
--ink:      #0C1220;   /* headlines, body */
--violet:   #6C2BD9;   /* the accent */
--steel:    #7E97BE;   /* fiber / labels */
--deep:     #080D1A;   /* dark panels */
```

To see your changes, open the `.html` in a browser. It shows the sheets on a grey desk, at the size
they will print, with a note at the top that never prints.

## Printing

Browser → Print → **Save as PDF**, then:

- **Margins: None**
- **Scale: 100%** (not "Fit to page")
- **Background graphics: on** — without this the dark panels come out white

Or regenerate the PDFs from the command line:

```bash
# needs: pip install playwright && playwright install chromium
python make-pdfs.py
```

### Brochure folding

Print both sheets **double-sided, flipping on the short edge**, then fold down the middle.
Sheet 1 is the outside — back cover on the left, front cover on the right. Sheet 2 is the inside
spread. Print one copy first and fold it before running the whole stack.

### Business card

The page is 91 × 61 mm: an 85 × 55 mm card plus 3 mm of bleed on every side. Send `card.pdf` to the
printer as it is. The dashed rectangle marks the trim edge and only appears on screen, never in the
PDF. Page 1 is the front, page 2 the back.

## Before you print

Same placeholders as the website:

- `github.com/qnest-toolkit/qnest` — appears on all three pieces
- The name, role and email on the back of the business card
- Contact details in the brochure back cover and the handout footer

## Images

All three pull from `../docs/images/`, so the print pieces and the website never drift apart. If you
replace a screenshot on the site, the print pieces pick it up too.
