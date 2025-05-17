import board, digitalio, adafruit_mpr121, busio, time, displayio, rgbmatrix, framebufferio
import adafruit_imageload, terminalio, random
import adafruit_display_text.label


displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64, bit_depth=2,
    rgb_pins=[board.GP0, board.GP1, board.GP2, board.GP3, board.GP4, board.GP5],
    addr_pins=[board.GP6, board.GP7, board.GP8, board.GP9],
    clock_pin=board.GP10, latch_pin=board.GP12, output_enable_pin=board.GP13)
display = framebufferio.FramebufferDisplay(matrix)


#i2c = busio.I2C(board.GP17, board.GP16)
#touch_pad = adafruit_mpr121.MPR121(i2c)


def scroll(line):
    line.x = line.x - 1
    line_width = line.bounding_box[2]
    if line.x < -line_width:
        line.x = display.width


def reverse_scroll(line):
    line.x = line.x + 1
    line_width = line.bounding_box[2]
    if line.x >= display.width:
        line.x = -line_width


def dsum(l): #Gets the sum of the dummy list, if 0 then the display is black
    nreturn = 0
    for i in l:
        nreturn = nreturn + i
    return nreturn
   
def displaybmp(filename): #Displays a bmp on your board
    g = displayio.Group()
    b, p = adafruit_imageload.load(filename)
    t = displayio.TileGrid(b, pixel_shader=p)
    if b.width >= 64:
        t.x = 0
    else: #Centers bmps smaller than 64 width
        t.x = round((64 - b.width)/2)
    if b.height >= 32:
        t.y = 0
    else: #Same but for height
        t.y = round((32 - b.height)/2)
    g.append(t)
    display.root_group = g


def apply_life_rule(old, new):
    width = old.width
    height = old.height
    for y in range(height):
        yyy = y * width
        ym1 = ((y + height - 1) % height) * width
        yp1 = ((y + 1) % height) * width
        xm1 = width - 1
        for x in range(width):
            xp1 = (x + 1) % width
            neighbors = (
                old[xm1 + ym1] + old[xm1 + yyy] + old[xm1 + yp1] +
                old[x   + ym1] +                  old[x   + yp1] +
                old[xp1 + ym1] + old[xp1 + yyy] + old[xp1 + yp1])
            new[x+yyy] = neighbors == 3 or (neighbors == 2 and old[x+yyy])
            xm1 = x


def randomize(output, fraction=0.33):
    for i in range(output.height * output.width):
        output[i] = random.random() < fraction


def conway(output):
    conway_data = [
        b'  +++   ',
        b'  + +   ',
        b'  + +   ',
        b'   +    ',
        b'+ +++   ',
        b' + + +  ',
        b'   +  + ',
        b'  + +   ',
        b'  + +   ',
    ]
    for i in range(output.height * output.width):
        output[i] = 0
    for i, si in enumerate(conway_data):
        y = output.height - len(conway_data) - 2 + i
        for j, cj in enumerate(si):
            output[(output.width - 8)//2 + j, y] = cj & 1


SCALE = 1
b1 = displayio.Bitmap(display.width//SCALE, display.height//SCALE, 2)
b2 = displayio.Bitmap(display.width//SCALE, display.height//SCALE, 2)
palette = displayio.Palette(2)
tg1 = displayio.TileGrid(b1, pixel_shader=palette)
tg2 = displayio.TileGrid(b2, pixel_shader=palette)
g1 = displayio.Group(scale=SCALE)
g1.append(tg1)
display.root_group = g1
g2 = displayio.Group(scale=SCALE)
g2.append(tg2)


#A list of bmp filenames I used
pixelart = ["PICO.bmp"]
nyan = ["PICO.bmp"]
bmps = ["PICO.bmp"]
pixelpath = "bmps/"
nyanpath = "bmps/"
bmpspath = "bmps/"
x = time.time()
dummy = [0, 0, 0, 0, 0]
firsttimeconway = True
randomindex = random.randint(0, len(bmps)-1)
newpress = True
lastindex = 0 #Used as a counter in the slideshow below
while True: #Because the Pico is a simpler board, you need to hold down on the cap touch sensors until your input is registered
    y = time.time()
    touch_pad = [0, 0, 0, 0, 0, 0]
    r = random.randint(0, len(touch_pad)-1)
    touch_pad[r] = 1
    if touch_pad[0]:
        print("10")
        dummy = [0, 0, 0, 0, 0]
    if touch_pad[1]: #Triggers the first scroller
        dummy = [1, 0, 0, 0, 0]
    if touch_pad[2]: #Triggers the game of life
        dummy = [0, 1, 0, 0, 0]
        firsttimeconway = True
    if touch_pad[3]: #Triggers a random image from the bmp folder
        dummy = [0, 0, 1, 0, 0]
        newpress = True
    if touch_pad[4]: #A nyan cat animation
        dummy = [0, 0, 0, 1, 0]
    if touch_pad[5]: #Triggers a slideshow of images from the bmp folder
        dummy = [0, 0, 0, 0, 1]
    matrix.brightness = dsum(dummy)
    if dummy[0] == 1: #A text scroller
        scrollert = time.time()
        line1 = adafruit_display_text.label.Label(
            terminalio.FONT,
            color=0xff0000,
            text="CircuitPython")
        line1.x = display.width
        line1.y = 8
        line2 = adafruit_display_text.label.Label(
            terminalio.FONT,
            color=0x0080ff,
            text="On RP Pico")
        line2.x = display.width
        line2.y = 24
        g = displayio.Group()
        g.append(line1)
        g.append(line2)
        display.root_group = g
        while time.time() < scrollert + 5:
            scroll(line1)
            reverse_scroll(line2)
            display.refresh(minimum_frames_per_second=0)
    if dummy[1] == 1: #Conway's game of life code by Jeff Epler https://learn.adafruit.com/rgb-led-matrices-matrix-panels-with-circuitpython/example-conways-game-of-life
        conwayt = time.time()
        if firsttimeconway:
            palette[1] = 0xffffff
            conway(b1)
            firsttimeconway = False
        display.auto_refresh = True
        time.sleep(3)
        n = 40
        while time.time() < conwayt + 5: #Change color and check for new input every 10 secs
            for _ in range(n):
                display.root_group = g1
                apply_life_rule(b1, b2)
                display.root_group = g2
                apply_life_rule(b2, b1)
            randomize(b1)
            palette[1] = (
                (0x0000ff if random.random() > .33 else 0) |
                (0x00ff00 if random.random() > .33 else 0) |
                (0xff0000 if random.random() > .33 else 0)) or 0xffffff
            n = 200
    if dummy[2] == 1: #Display a random bmp from the folder
        if newpress:
            randomindex = random.randint(0, len(bmps)-1)
            newpress = False
        filename2 = bmpspath + bmps[randomindex]
        displaybmp(filename2)
        time.sleep(1) #Pause so you don't hold down accidentally
    if dummy[3] == 1: #Nyan cat animation
        nyant = time.time()
        while time.time() < nyant + 5:
            for i in nyan:
                filename3 = nyanpath + i
                displaybmp(filename3)
                time.sleep(.01)
    if dummy[4] == 1: #A slideshow of images, t secs in between images
        slideshowt = time.time()
        t = 5
        while time.time() < slideshowt+5:
            if lastindex == len(pixelart)-1:
                filename4 = pixelpath + pixelart[lastindex]
                displaybmp(filename4)
                time.sleep(t)
                lastindex = 0
            else:
                filename4 = pixelpath + pixelart[lastindex]
                displaybmp(filename4)
                time.sleep(t)
                lastindex += 1
