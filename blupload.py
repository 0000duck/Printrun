import printcore,time,sys,os

def dosify(name):
    return name[:8]+".g"

def blupload(printer,filename,path):
    printer.send_now("M28 "+dosify(filename))
    printer.startprint([i.replace("\n","") for i in open(path)])
    try:
        sys.stdout.write("Progress: 00.0%")
        sys.stdout.flush()
        while(printer.printing):
            time.sleep(1)
            sys.stdout.write("\b\b\b\b%02.1f%%" % (100*float(printer.queueindex)/len(printer.mainqueue),) )
            sys.stdout.flush()
        printer.send_now("M29 "+dosify(filename))
    except:
        printer.disconnect()

if __name__ == '__main__':
    #print "Usage: python blupload.py filename.gcode"
    filename="../prusamendel/sellsx_export.gcode"
    tfilename=filename
    if len(sys.argv)>1:
        filename=sys.argv[1]
        tfilename=os.path.basename(sys.argv[1])
        print "Uploading: "+filename," as "+dosify(tfilename)
        p=printcore.printcore('/dev/ttyUSB0',115200)
        p.loud=True
        time.sleep(2)
        blupload(p,tfilename,filename)
    else:
        print "Usage: python blupload.py filename.gcode"

