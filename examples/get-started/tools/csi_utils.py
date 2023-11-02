import math
import sys

def SQR(vv):
    return vv*vv

def SQRRT(vv, tt):
    return math.sqrt(vv*vv + tt*tt)

def strpad(strx, lenx):
    lll = len(strx)
    if lenx <= lll:
        return strx
    return strx + ' ' * (lenx-lll)

def parr(namex, arrx):
    print (namex, end= ' ')
    for aa in arrx[6:9]:
        print(aa[6:9])

#PI = 3.1415926
PI = math.pi


def deangle(xx, yy):

    '''if xx == 0.:
        if yy > 0.:
            uuu = math.degrees(0)
        else:
            uuu = math.degrees(PI)
        return  uuu

    if yy == 0.:
        if xx > 0.:
            uuu = math.degrees(PI/2)
        else:
            uuu = math.degrees(PI+PI/2)
        return uuu
    '''
    try:
        uuu = math.degrees(math.atan2(yy, xx))
    except:
        uuu = 0
        print(sys.exc_info())
    return uuu

    # ------------------------------------------------------------------------
    #                       yy
    #                 +-     |   ++
    #  PI + PI/2  -----------|----------- xx    PI/2
    #                 --     |   +-
    #                       PI


    if xx >= 0. and yy >= 0.:
        dd = abs(xx) / abs(yy)
        uu = math.atan(dd)
        uu += 0
    elif xx >= 0. and yy <= 0.:
        dd = abs(xx) / abs(yy)
        uu = math.atan(dd)
        uu += PI/2
    elif xx <= 0. and yy <= 0.:
        dd = abs(xx) / abs(yy)
        uu = math.atan(dd)
        uu += PI
    elif xx <= 0. and yy >= 0.:
        dd = abs(xx) / abs(yy)
        uu = math.atan(dd)
        uu += PI + PI/2
    else:
        pass
        #
        print("unexpected sign",vv, tt)

    uuu = math.degrees(uu)
    #print(uu, uuu)

    return uuu

