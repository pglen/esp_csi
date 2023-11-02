import math
from csi_utils import  *
import matplotlib.pyplot as plt

cnt = 0; cntarr = []
yyarr  = []
yyarr2 = []

for aa in range (-8, 8,):
    if 1: #for bb in range (-8, 8):
        val = deangle(1, aa)
        val2 = deangle(aa, 1)
        #print ( '%+2d %+2d %+.2f' % (aa, bb, val), end = '  ')
        '''try:
            print ( '%+2d %+2d %+.2f' % (aa, bb, math.degrees(math.atan(aa / bb))), end = ' -  ')
        except:
            pass
        '''
        #if cnt % 4 == 3:
        #    print()

        cnt += 1
        cntarr.append(aa)
        yyarr.append(val)
        yyarr2.append(val2)

plt.plot(cntarr, yyarr)
plt.plot(cntarr, yyarr2)
plt.show()

#for aa in range (-12, 12):
#        print (aa, 1, deangle(aa, 1))

