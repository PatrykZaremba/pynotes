from tinydb import TinyDB, Query
import flet as ft
from datetime import date
import re
import base64

db = TinyDB("data")
qry = Query()

notes = db.table("Notes")
tags = db.table("Tags")

def getTags(special_option = None, exclude_list : list = None):
    '''Function for returning list of Dropdown options for various dropdown controls'''
    new_tag_list = []
    if special_option:
        new_tag_list.extend(special_option)

    if exclude_list != None:
        for tag_document in tags.all():
            if not tag_document["tag"] in exclude_list:
                new_tag_list.append(tag_document["tag"])
    else:
        for tag_document in tags.all():
            new_tag_list.append(tag_document["tag"])
    tag_options = []
    for tag in new_tag_list:
        tag_options.append(ft.DropdownOption(tag))
    return tag_options

############################################################################################################################

class TagsEditor(ft.AlertDialog):
    '''Main way of managing the tags'''
    def __init__(self, page, note_update = None):
        super().__init__()
        # Transfer variables
        self.page = page
        self.note_update = note_update
        # Setup the control
        self.title = ft.Text("All Tags")
        self.content = ft.ListView(width=512)
        self.actions = [ft.Button("Save", on_click=self.save), ft.Button("Close", on_click=self.cancel)]
        # Add all existing tags
        for tag_document in tags.all():
            self.content.controls.append(ft.Row([ft.IconButton(icon=ft.Icons.REMOVE, on_click=self.removeTag), ft.TextField(value=tag_document["tag"], expand=True)]))
        self.content.controls.append(ft.CupertinoButton("New Tag", on_click=self.addTag, icon=ft.Icons.ADD))

    def cancel(self, e):
        '''Cancel all changes'''
        self.page.close(self)
    
    def save(self, e):
        '''Commit and save all changes'''
        all_tags = tags.all()
        # Remove all old tags
        documents_to_remove = []
        for doc in all_tags:
            documents_to_remove.append(doc.doc_id)
        tags.remove(doc_ids=documents_to_remove)
        # Add all new tags
        documents_to_add = []
        for row in self.content.controls:
            if not isinstance(row, ft.CupertinoButton):
                documents_to_add.append({"tag": row.controls[1].value})
        tags.insert_multiple(documents_to_add)
        self.note_update()
        self.page.close(self)
    
    def removeTag(self, e):
        '''Remove tag from the local list'''
        self.content.controls.remove(e.control.parent)
        self.content.update()
    
    def addTag(self, e):
        '''Add new tag to local list'''
        self.content.controls.insert(len(self.content.controls)-1, ft.Row([ft.IconButton(icon=ft.Icons.REMOVE, on_click=self.removeTag), ft.TextField(value="", expand=True)]))
        self.content.update()

############################################################################################################################

class NewTag(ft.AlertDialog):
    '''Simple version of Tag Editor allowing only to add a single Tag'''
    def __init__(self, page, reopener = None):
        super().__init__()
        # Transfer variables
        self.page = page
        self.reopener = reopener
        self.title = ft.Text("New Tag")
        # Setup the control
        self.content = ft.TextField(label="New Tag Name")
        self.actions = [ft.Button("Create New", on_click=self.create), ft.Button("Cancel", on_click=self.cancel)]
    
    def cancel(self, e):
        '''Cancel all changes'''
        if self.reopener:
            self.page.open(self.reopener)
    
    def create(self, e):
        '''Commit and create the new tag in database'''
        tags.insert({"tag": self.content.value})
        if self.reopener:
            self.page.open(self.reopener)
            self.reopener.addTag(ft.ControlEvent("", "", self.content.value, ft.Text(), self.page))
        else:
            self.page.close(self)
        self.content.value = ""
        self.content.update()

############################################################################################################################

class NoteEditor(ft.AlertDialog):
    '''Main way of writing notes'''
    def __init__(self, page, file_picker = None, title = "", tags = None, multimedia = None, note = "", docid = None, note_update = None):
        super().__init__()
        # Transfare the variables
        self.note_update = note_update
        self.docid = docid
        self.page = page
        self.image_dialog : ft.FilePicker = file_picker
        self.image_dialog.on_result = self.pickedImage
        self.modal = True
        # Simple vatiables
        self.note_title = ft.TextField(value=title, label="Note Title (Optional)")
        self.note_content = ft.TextField(value=note, label="Note Content", multiline=True, min_lines=5)
        self.upload_button = ft.IconButton(ft.Icons.UPLOAD_FILE, on_click=self.promptImage)
        self.multimedia = ft.Column(expand=True)
        self.new_tag = NewTag(page, self)
        self.tags = ft.Row(expand=True, scroll=ft.ScrollMode.ALWAYS)
        # Loading all previous elements 
        self.exclude_tags = []
        if multimedia:
            for media in multimedia:
                self.multimedia.controls.append(ft.Stack([ft.Image(src_base64=media, fit=ft.ImageFit.FIT_WIDTH, width=self.page.width*0.75), ft.Button("Remove", on_click=self.delete_self)]))
        for tag in tags:
            self.exclude_tags.append(tag)
            self.tags.controls.append(ft.Button(tag, on_click=self.removeTag))
        self.tag_drop = ft.Dropdown(options=getTags(special_option=["Create New Tag"], exclude_list=self.exclude_tags), on_change=self.addTag)
        # Setup the control
        self.title = ft.Text("Note Editor")
        self.content = ft.Column(width=1024, controls=[
            self.note_title,
            ft.Row([self.tag_drop, self.tags]),
            self.note_content,
            self.multimedia,
            self.upload_button
            ], scroll=ft.ScrollMode.ALWAYS, expand=True)
        self.actions = [ft.Button("Save", on_click=self.save), ft.Button("Cancel", on_click=self.cancel)]
        # Add remove button if editing
        if self.docid!= None:
            self.actions.append(ft.Button("Remove", on_click=self.remove, color=ft.Colors.RED_ACCENT))
    
    def cancel(self, e = None):
        '''Cancel all changes to the note'''
        self.page.close(self)
    
    def save(self, e = None):
        '''Save the note'''
        current_tags = []
        for each in self.tags.controls:
            current_tags.append(each.text)
        current_images = []
        for each in self.multimedia.controls:
            current_images.append(each.controls[0].src_base64)
        if self.docid:
            notes.update({"note_title": self.note_title.value, "note_tags": current_tags, "note_content": self.note_content.value, "note_media" : current_images,  "note_edited": date.today().strftime("%d/%m/%Y")}, doc_ids=[self.docid])
        else:
            notes.insert({"note_title": self.note_title.value, "note_tags": current_tags, "note_content": self.note_content.value, "note_media" : current_images, "note_edited": date.today().strftime("%d/%m/%Y")})
        self.note_update()
        self.page.close(self)
    
    def remove(self, e = None):
        '''Remove the note entirely'''
        notes.remove(doc_ids=[self.docid])
        self.note_update()
        self.page.close(self)

    def delete_self(self, e):
        '''Helper for images to be able to delete themselves'''
        self.multimedia.controls.remove(e.control.parent)
        self.multimedia.update()

    def pickedImage(self, e : ft.FilePickerResultEvent):
        '''Function for when user has picked an image'''
        file = e.files[0]
        file_encoded = ""
        with open(file.path, "rb") as img_file:
            file_encoded = base64.b64encode(img_file.read()).decode('utf-8')
        self.multimedia.controls.append(ft.Stack([ft.Image(src_base64=file_encoded, fit=ft.ImageFit.FIT_WIDTH, width=self.page.width*0.75), ft.Button("Remove", on_click=self.delete_self)]))
        self.multimedia.update()

    def promptImage(self, e):
        '''Function to open the file dialog'''
        self.image_dialog.pick_files(dialog_title="Open Image", file_type=ft.FilePickerFileType.IMAGE, allow_multiple=False)

    def addTag(self, e : ft.ControlEvent):
        '''Add tag to current note'''
        if e.data == "Create New Tag":
            self.page.open(self.new_tag)
            return
        self.tags.controls.append(ft.Button(e.data, on_click=self.removeTag))
        self.exclude_tags.append(e.data)
        self.tag_drop.options = getTags(special_option=["Create New Tag"], exclude_list=self.exclude_tags)
        self.tag_drop.update()
        self.tags.update()

    def removeTag(self, e : ft.TapEvent):
        '''Remove tag from current note'''
        self.exclude_tags.remove(e.control.text)
        self.tags.controls.remove(e.control)
        self.tag_drop.options = getTags(special_option=["Create New Tag"], exclude_list=self.exclude_tags)
        self.tag_drop.update()
        self.tags.update()

############################################################################################################################

def main(page : ft.Page):
    '''Main function that runs whenever the application starts'''
    # GUI functions for later use
    def swapTheme(e = None):
        '''Change the theme of application'''
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
        page.update()

    def editNote(e = None):
        '''Opens note editor, either with new note or editing existing note'''
        if e.control.data != None:
            doc = notes.get(doc_id=e.control.data)
            note_editor = NoteEditor(page, image_picker, doc["note_title"], doc["note_tags"], doc["note_media"], doc["note_content"], doc.doc_id, updateNotes)
            page.open(note_editor)
        else:
            n_tags = []
            if not tag_search.value in special_tags:
                n_tags.append(tag_search.value)
            note_editor = NoteEditor(page, image_picker, tags=n_tags, note_update=updateNotes)
            page.open(note_editor)

    def updateNotes(e = None):
        '''Update all notes displayed as well as the tags'''
        filer_tag = tag_search.value
        filer_text = text_search.value
        notes_display.controls.clear()
        if (filer_tag == "All"):
            docs = notes.search(qry["note_content"].matches(f"(.|\n)*{filer_text}(.|\n)*", flags=re.IGNORECASE) | qry["note_title"].matches(f"(.|\n)*{filer_text}(.|\n)*", flags=re.IGNORECASE))
        else:
            docs = notes.search(qry["note_tags"].any([filer_tag]) & (qry["note_content"].matches(f"(.|\n)*{filer_text}(.|\n)*", flags=re.IGNORECASE) | qry["note_title"].matches(f"(.|\n)*{filer_text}(.|\n)*", flags=re.IGNORECASE)))
        new_notes = []

        for note in docs:
            if filer_text != "":
                if filer_text.casefold() in note["note_title"].casefold():
                    n_title = note["note_title"]
                if filer_text.casefold() in note["note_content"].casefold():
                    index = note["note_content"].casefold().find(filer_text.casefold())
                    n_title = note["note_content"][max(index-50, 0):min(index+50, len(note["note_content"]))].replace("\n", "  ")
            else:
                if note["note_title"] != "":
                    n_title = note["note_title"]
                else:
                    n_title = note["note_content"][:100].replace("\n", "  ")
            n_media = []
            for each in note["note_media"]:
                n_media.append(ft.Image(src_base64=each, fit=ft.ImageFit.FIT_WIDTH, width=page.width*0.9))
            n_content = [ft.Row([ft.IconButton(ft.Icons.EDIT, data=note.doc_id, on_click=editNote, tooltip="Edit Note"), ft.Text("Tags: "+", ".join(note["note_tags"]))]), ft.Row([ft.Text(note["note_content"])]), ft.Row([ft.Column(n_media)]), ft.Text("Edited: "+note["note_edited"])]
            new_notes.append(ft.ExpansionTile(title=ft.Text(n_title), controls=n_content))
        notes_display.controls = new_notes
        notes_display.update()
        tag_search.options = getTags(special_tags)
        tag_search.update()
    
    def editTags(e = None):
        '''Open tag editor'''
        tag_editor = TagsEditor(page, updateNotes)
        page.open(tag_editor)
    # Page setup
    page.title = "PyNotes"
    page.theme_mode = ft.ThemeMode.DARK
    page.appbar = ft.AppBar(leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE), title=ft.Text("PyNotes"), actions=[ft.IconButton(ft.Icons.WB_SUNNY_OUTLINED, on_click=swapTheme)])
    body = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS)
    # Magic variables
    special_tags = ["All", "Drafts"]
        
    # Creation of components
    image_picker = ft.FilePicker()
    text_search = ft.TextField(on_submit=updateNotes, label="Search in text")
    tag_search = ft.Dropdown(editable=True, on_change=updateNotes, label="Filter by tag")
    search_bar = ft.Row([ft.IconButton(ft.Icons.SEARCH, on_click=updateNotes), text_search, tag_search, ft.IconButton(ft.Icons.ADD, on_click=editNote, tooltip="New Note"), ft.IconButton(ft.Icons.LABEL, on_click=editTags, tooltip="Edit Tags")])
    notes_display = ft.Column()

    # Finalise page
    body.controls.append(search_bar)
    body.controls.append(notes_display)
    page.add(body)
    page.add(image_picker)
    tag_search.options = getTags(special_tags)
    tag_search.value = "All"
    tag_search.update()
    updateNotes(None)

############################################################################################################################

ft.app(main)