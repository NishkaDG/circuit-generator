#Converts any S-Box (any number of bits) to a set of individual functions and vice-versa.
#If the S-Box has 2^n entries, this program returns n functions (decimal representations of the functions).
#If the function has n outputs/columns, this program returns an S-Box with 2^n entries.

from math import log2

#Python truncates the binary representation of integers by omitting leading 0s.
#This function extends the binary representation to the required number of bits by adding leading 0s if necessary.
def bitExtended(num, nB):
    inBinary = bin(num)
    bitsOnly = inBinary[inBinary.index('b')+1:]
    remainder = 0
    if len(bitsOnly)<nB:
        remainder = nB-len(bitsOnly)
        prefix = '0'*remainder
        #print(prefix)
        bitsOnly = prefix+bitsOnly
    #print(bitsOnly)
    return bitsOnly

#Transposes the matrix.
def transpose(matrix):
    tt = [list(i) for i in zip(*matrix)]
    return tt

#Returns the decimal value of a list of boolean strings.
def getDecimal(m):
    col = ''
    sValues = []
    for row in m:
        for i in row:
            col = col+i
        sValues.append(int(col, base=2))
        col = ''
    return sValues

#Converts an S-Box to a set of functions.
def sBoxToColumns(sb):
    trans = []
    numRows = len(sb)
    numCols = int(log2(numRows))
    for item in sb:
        itemExtended = bitExtended(item, numCols)
        trans.append(itemExtended)
    truthtable = transpose(trans)
    decVal = getDecimal(truthtable)
    return decVal

#Converts a set of n functions to an S-Box with 2^n values.
def funcToSBox(fn):
    trans = []
    numCols = len(fn)
    numRows = 2**numCols
    for item in fn:
        itemExtended = bitExtended(item, numRows)
        trans.append(itemExtended)
    truthtable = transpose(trans)
    decVal = getDecimal(truthtable)
    return decVal

#print(sBoxToColumns([12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]))
#print(funcToSBox([39792, 57708, 13029, 22950])
#print(funcToSBox([1020, 3855, 13107, 43690]))
