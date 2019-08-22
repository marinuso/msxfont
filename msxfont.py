#!/usr/bin/env python

#### MSXFONT ####
# MSX Font Editor 
# by Marinus Oosters

import sys
from Tkinter import *
from ttk import *
import tkMessageBox
import tkFileDialog


FONTSCALE=3

def toBits(num):
    """Get an 8-bit binary array for a number"""
    bits = [False]*8 
    for i in range(8):
        bits[7-i] = bool(num & 1<<i)
    return bits
    
def fromBits(bits):
    """Turn a binary array into a number"""
    result = 0
    for bit in reversed(bits):
        result *= 2
        result += bit
    return result 
    
def bitsToImage(bits,image=None,scale=FONTSCALE):
    """Turns an array of bit arrays into an image"""
    width = len(bits)*scale
    height = len(bits[0])*scale 
    if image==None: 
        image = PhotoImage(width=width, height=height)
    pixels = []
    for line in bits:
        for _ in range(scale):
            pixels.append('{')
            for bit in line:
                for _ in range(scale):
                    pixels.append(["#000000","#FFFFFF"][bit])
            pixels.append('}')
    image.put(" ".join(pixels),(0,0,width,height))
    return image 
    
class MSXFont(object):
    """MSX font"""
    
    @staticmethod
    def load(filename):
        with file(filename) as f:
            data = map(ord, f.read())
            return MSXFont(data)
    
    def __init__(self, data=[0]*2048):
        if len(data) != 2048:
            raise IOError("invalid font data")
        self._data = data[:]
    
    def save(self, filename):
        with file(filename, 'w') as f:
            f.write(''.join(map(chr, self._data)))
    
    
    
    # get and set values
    def __getitem__(self, (item, x, y)):
        if not (0<=x<8 and 0<=y<8):
            raise IndexError("coordinate out of range: %d,%d" % (x,y))
        letter = self._data[item*8 + y];
        return bool(letter & (1<<7-x))
    
    def __setitem__(self, (item, x, y), value):
        if not (0<=x<8 and 0<=y<8):
            raise IndexError("coordinate out of range: %d,%d" % (x,y))
        cur = self._data[item*8 + y]
        cur &= 255 ^ 1<<7-x      # turn off bit under consideration
        cur |= bool(value)<<7-x  # turn it on if value is true 
        self._data[item*8 + y]=cur


    # get and set letters
    def getLetter(self, letter):
        if not 0<=letter<256:
            raise IndexError("letter out of range: %d" % letter)
        l = []
        for i in range(8):
            l.append(toBits(self._data[letter*8 + i]))
        return l
   
    def setLetter(self, letter, newBits):
        if not 0<=letter<256:
            raise IndexError("letter out of range: %d" % letter)
        if len(newBits)!=8:
            raise FormatError("a letter has 8 bytes, not %d" % len(newBits))
        for i in range(8):
            self._data[letter*8 + i] = fromBits(newBits[i])

### UI

def saveChangesDialog(parent):
    retval = [0]
    top = Toplevel(parent)
    top.resizable(width=FALSE, height=FALSE)
    
    def cancel(): 
        retval[0]=0
        top.destroy()
    def save(): 
        retval[0]=1 
        top.destroy()
    def discard(): 
        retval[0]=2
        top.destroy()
    
    lbl = Label(top, text="Do you want to save changes to the current font?")
    lbl.pack(padx=5, pady=5)
    
    Button(top, text='Save', command=save).pack(side=RIGHT, padx=5, pady=5)
    Button(top, text='Discard', command=discard).pack(side=RIGHT, padx=5, pady=5)
    Button(top, text='Cancel', command=cancel).pack(side=RIGHT, padx=5, pady=5)
    
    parent.wait_window(top)
    return retval[0]
   

class FontWindow(Frame):
    filename = ''
    font = MSXFont() 
    font_canvas = None 
    font_imgs = [None]*256
    editor_bits = [None]*64
    select_rectangle = None 
    selectedItem = 0
    modified = False 
    
    
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.parent = parent 
        self.initUI()

    def initUI(self):
        self.parent.title("MSX Font Editor")
        self.style = Style()
        self.style.theme_use("default")
        self.pack(fill=BOTH, expand=1)
        
        menubar = Menu(self.parent)
        self.parent.config(menu=menubar)
        fileMenu = Menu(menubar)
        fileMenu.add_command(label="New", command=self.file_new)
        fileMenu.add_command(label="Open...", command=self.file_open)
        fileMenu.add_command(label="Save",  command=self.file_save)
        fileMenu.add_command(label="Save As...", command=self.file_save_as)
        fileMenu.add_command(label="Quit", command=self.file_quit)
        menubar.add_cascade(label="File", menu=fileMenu)
        
        # create font canvas frame
        fcf = Frame(self)
        fcf.pack(fill=BOTH, side=LEFT, expand=1)
        
        # label
        self.fclabel = Label(fcf, text="Selection goes here")
        self.fclabel.pack(fill=BOTH, padx=4, pady=4)
        # create font canvas
        self.font_canvas = Canvas(fcf, width=16*8*FONTSCALE, height=16*8*FONTSCALE)
        self.font_canvas.pack()
        self.font_canvas.bind('<Button-1>', self.font_canvas_Click)
        
        # create font images 
        for i in range(256):
            #self.font_imgs[i] = bitsToImage(self.font.getLetter(i))
            self.font_imgs[i] = PhotoImage(width=8*FONTSCALE, height=8*FONTSCALE)
            xloc = (i&15) * 8 * FONTSCALE
            yloc = (i>>4) * 8 * FONTSCALE
            self.font_canvas.create_image(xloc, yloc, image=self.font_imgs[i], anchor=NW)
            
        self.select_rectangle = self.font_canvas.create_rectangle(0, 0, 8*FONTSCALE, 8*FONTSCALE, 
                                        outline="#f00", width=2)
         
        # create editor canvas
        ecf = Frame(self)
        ecf.pack(fill=BOTH, side=RIGHT, expand=1)
        self.edlabel = Label(ecf, text="Font editor")
        self.edlabel.pack(fill=BOTH, padx=4, pady=4)
        
        self.editor_canvas = Canvas(ecf, width=16*8*FONTSCALE, height=16*8*FONTSCALE)
        self.editor_canvas.pack()
        self.editor_canvas.bind('<Button-1>', self.editor_canvas_Click)
            
        # create selection bits
        for i in range(64):
            xloc = (i&7)*16*FONTSCALE 
            yloc = (i>>3)*16*FONTSCALE  
            self.editor_bits[i] = self.editor_canvas.create_rectangle(
                                xloc, yloc, xloc+16*FONTSCALE, yloc+16*FONTSCALE,
                                fill="#000")                                
        
        self.updateFontImages()            
        self.updateSelection()
        
    def editor_canvas_Click(self, event):
        # toggle item under cursor
        xloc = int(event.x / (16*FONTSCALE))
        yloc = int(event.y / (16*FONTSCALE))
        
        # get new pixel value
        newval = not self.font[self.selectedItem, xloc, yloc]
        
        # set the bit under the cursor
        self.editor_canvas.itemconfig(
                 self.editor_bits[yloc*8 + xloc], fill=["#000","#FFF"][newval])
        
        # set new pixel value in font
        self.font[self.selectedItem, xloc, yloc] = newval
        
        # update the image in the selection canvas
        self.updateFontImage(self.selectedItem)
        
        self.modified = True 
        
          
    def font_canvas_Click(self, event):
        # select another item
        xloc = int(event.x / (8*FONTSCALE))
        yloc = int(event.y / (8*FONTSCALE))

        self.selectedItem = yloc*16 + xloc
        self.updateSelection()
        
            
    def updateFontImage(self, i):
        bitsToImage(self.font.getLetter(i), self.font_imgs[i])
        
    def updateFontImages(self):
        for i in range(256):
            self.updateFontImage(i)
    
    def updateSelection(self):
        xloc = self.selectedItem & 15
        yloc = self.selectedItem >> 4
        self.font_canvas.coords(self.select_rectangle, (
             xloc*8*FONTSCALE, yloc*8*FONTSCALE, 
             (xloc+1)*8*FONTSCALE, (yloc+1)*8*FONTSCALE))
             
        self.fclabel["text"] = "Selected item: %d (%X)" % (self.selectedItem, self.selectedItem)
        
        
        bits = self.font.getLetter(self.selectedItem)
        
        for n, bit in zip(range(64), sum(bits, [])):
            self.editor_canvas.itemconfig(self.editor_bits[n], fill=["#000","#FFF"][bit])
            
        
    def loadFont(self, filename, font):
        self.filename = filename
        self.font = font
        self.selectedItem = 0
        self.modified = False 
        self.updateFontImages()
        self.updateSelection()
        
    def file_new(self):
        if self.modified:
            ans = saveChangesDialog(self)
            print ans 
            if ans == 0: return # cancel
            if ans == 2: self.file_save() # save
        
        self.loadFont('', MSXFont())
           
    def file_open(self):
        file = tkFileDialog.askopenfilename()#self, filetypes=[('All files', '*')])
        if file != '':
            try: 
                font = MSXFont.load(file)
                self.loadFont(file, font)
            except Exception, e:
                tkMessageBox.showerror("Error opening file", 
                       "Error opening file '%s':\n%s"%(file,e.message))
          
    def file_save(self):
        if self.filename == '': 
            self.file_save_as()
            return
        
        try:
            self.font.save(self.filename)
            self.modified = False 
        except Exception, e:
            tkMessageBox.showerror("Error saving file", 
                        "Error saving file '%s':\n%s"%(self.filename,e.message))          

    def file_save_as(self):
        file = tkFileDialog.asksaveasfilename()#self, filetypes=[('All files', '*')])
        if file != '':
            self.filename = file
            self.file_save()
            
    def file_quit(self):
        if self.modified:
            ans = saveChangesDialog(self)
            print ans 
            if ans == 0: return # cancel
            if ans == 2: self.file_save() # save
        
        sys.exit(0)        
            
    
def main(argv):
    font=None 
    if len(argv)==2:
        fn = argv[1]
        try:
            font = MSXFont.load(fn)
        except Exception, e:
            sys.stderr.write("Cannot load font: %s" % e.message)
            sys.exit(1)
            
    root = Tk()
    root.geometry("%dx%d" % ( 2*16*8*FONTSCALE+4, 16*8*FONTSCALE+25 ))
    root.resizable(width=FALSE, height=FALSE)
    app = FontWindow(root)
    if font:
        app.loadFont(argv[1], font)
    root.mainloop()

if __name__=='__main__':
    main(sys.argv)    
        