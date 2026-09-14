# Lakes of Bendakaluru - design direction

Status: approved and built, 2026-09-14.
Chosen territory: B, cut paper, in its "one lake, cut out" form.

## Concept

One lake, cut out, a new one every visit.
Every lake is a sheet of coloured paper, cut at its real outline and laid on a cream table.
The paper's colour is the valley its water runs down.
Facts about the lake are paper slips pinned on top.
Nothing else is on the page.

## Opening screen

Each visit picks a random lake and fills the screen with it.
The lake is drawn so the biggest open area inside it is 640 px wide on a laptop and 290 px on a phone, always in the same spot.
The lake's name is fitted into that area, between 96 and 190 px.
The rest of the lake runs off the page wherever its shape takes it.
The layout is computed at build time for every lake, so the page never has to guess.

On top, as pasted paper:
- Six fact slips: size in acres and football pitches, rank by size, valley, who looks after it, water quality, how much is built over.
- A stamp "Residents are organising here" when a citizen campaign exists.
- A dotted end-to-end measure across the lake with its length.
- A locator: every lake in the city as a dot, this one circled.
- A scale bar and the lake's ward and coordinates.
- The main button "See all lakes", ink paper with cream text.
- A smaller "Show me another" that picks a new lake without leaving the page.

Missing data is shown, in italic grey: "Nobody on record looks after it", "Not tested for water quality yet".

## Mark

The wordmark "Lakes of Bendakaluru" in Instrument Serif italic.
Ink on cream, or cream on any sheet.
There is no logo shape; the lake on screen is the picture.

## Type

Instrument Serif for lake names, slip values and headlines.
Instrument Sans for everything else.
Noto Serif Kannada for Kannada names.

| Use | Face | Size | Line height |
| --- | --- | --- | --- |
| Lake name | Instrument Serif | 96-190 px, fitted | 0.86 |
| Kannada name | Noto Serif Kannada 600 | a quarter of the name | 1.2 |
| Section headline | Instrument Serif | 64 px | 0.95 |
| Slip value | Instrument Serif | 36 px (26 on phone) | 1 |
| Button | Instrument Serif italic | 38 px (28 on phone) | 1 |
| Body | Instrument Sans 400 | 17 px | 1.55 |
| Label | Instrument Sans 400/500 | 12.5 px | 1.35 |

No capitals, no letter-spaced labels, no pill buttons.

## Colour

Table (page ground): cream #F6EEDB.
Ink #1B1A17, 15.1:1 on cream.
Missing-data grey #6F675A, 4.8:1 on cream.

Valley sheets, with the text colour that passes 3:1 for large text:

| Valley | Sheet | Text on it | Contrast |
| --- | --- | --- | --- |
| Koramangala-Challaghatta | #F2502B | cream | 3.1 |
| Hebbal | #FFC933 | ink | 11.3 |
| Vrishabhavathi | #2FA35B | ink | 5.4 |
| Dakshina Pinakini | #F59AC0 | ink | 8.5 |
| Suvarnamukhi | #7B4BD1 | cream | 4.8 |
| Arkavathi | #FF8A1F | ink | 7.4 |
| Other valleys (Kumudvathi, Kumadvati, Palar, Jayamangali, Shimsha, unnamed) | #11A3B5 | ink | 5.7 |
| No valley on record | #1F48D6 | cream | 6.2 |

The valley names are the ones the data computes, so the sheets follow the data rather than the other way round.

Small text never sits directly on a sheet; it sits on a cream slip.

## Paper

Sheets cast a soft brown shadow: 5 px right, 9 px down, 5 px blur, #5A3B12 at 30%.
Slips are cream, rotated between -1.8 and 1.8 degrees, with a hard 2 px/4 px shadow plus a soft drop.

## Spacing

4, 8, 12, 16, 24, 40, 64, 104.
Page edge 40 px on a laptop, 16 px on a phone.
No grid on the opening screen; the lake is the grid.
Inner pages use 12 columns with 24 px gutters.

## Imagery

Satellite view, turned grey and pushed 35% toward cream, with the lake laid on top in its valley's paper.
Used on the lake's own page, never on the opening screen.

## Motion

The lake lands like paper dropped on a table: it settles from 103% to full size while its shadow grows, 600 ms, once.
The slips follow 60 ms apart.
Nothing moves after that.

## Voice

Plain facts, said once.
Gaps in the record are stated as facts, not as outrage.
"Nobody on record looks after it."
"Bellandur does not fit on the page."

## Deliberate break

The lake is always bigger than the page and crosses every edge it wants to.
The headline lives inside the water.
