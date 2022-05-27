### Create/Edit User Index Tab
Here you create an index for books that have not yet been indexed or continue work on an index
you already started here. Books for indexing are shown in the table at the bottom of the left side of the tab.
By default this shows *Canonical Books - With No Index*. This can be changed with a *Settings* option though
the default setting is likely suitable for most needs.

<img src="Images/create-edit-user-index.png" width="400px" />

* Click the *Title Number* check box if the book you are indexing has *Title Numbers*, otherwise they will be considered *Sheet Numbers*. Remember, the distinction only concerns how the number is incremented on *Skip*.

* Click on a canonical book name in the *Canonical Books - With No Index* table. This will display the
  PDF file for that book in the PDF display. Page 1 is shown if this is the first time you are working on this book.
  The last page you indexed is shown if you are returning to a book on which you previously worked. 

    > Reminder, you have already entered a sheet and title for this page. Click the *Next* button to advance to the first page that has not been labeled.

* Draw a box around the title by left click and drag. The title will be processed by OCR and displayed in the *Title* box. Correct any OCR errors. Alternatively, you can type the title
in the *Title* box but there is little reason to do so when the title is clear and easily recognized.

* Enter the *Sheet/Title* number. This is the number printed in the book, not the PDF page number. On subsequent pages
the number will increment automatically. If the book does not have sheet/title numbers then, and only then, use the page number. 

* Right-Click and drag in the viewer window to magnify sheet numbers or other content that is too small to see.

  ![magnifier](/home/wrw/Dropbox/Work/Birdland/src/Documentation/Images/magnifier-crop.png)

* Click *Save* to save the current title but stay on the page. Appropriate when the page contains multiple titles.

* Click *Save+* to save the current title and advance to the next page. Appropriate when the page contains one
  title or on the last title when it contains multiple titles.

  > For both *Save* or *Save+* the current entry is added to the raw-index file and the sheet-offset file is updated.

* Click *Skip* to save a dummy title of *\__Skip__* and advance to the next page.  Appropriate
when the page contains a continuation of a page previously indexed page, a photo, or other non-titled content.
The *\__Skip__* title is a marker to indicate that the page was processed in the *Coverage Map* but is not included in the database.

* If the *Auto OCR* box is checked (the default) when *Save+* or *Skip* is
  clicked then the title selection box is retained and the content of that box on the next page is processed
  by OCR. This is appropriate where titles are in the same location on the page and are not obscured by
  staff lines.

* *Save*, *Save+*, and *Skip* require a title and sheet/title number to prevent inadvertent errors. For the same
reason they do not permit saving a title that has already been saved for the same page. You must first *Update* it
or *Delete* it.

* The navigation buttons *Go To*, *Prev*, *Next*, and *Last* have no such requirements. Be careful. *Last* navigates
to the last page indexed, not the last page in the book.

* Click on *Show Map* to display an index coverage map.

<img src="Images/index-coverage-map.png"/>

