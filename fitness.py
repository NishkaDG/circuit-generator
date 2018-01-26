#Walsh spectrum and autocorrelation spectrum.
#Works on 16-bit values only.
#Works for multi-output functions too.

#Also can be used to compute Hamming distance between two multi-output functions.
#Hamming distance computation works for all n-output functions, provided the functions to be compared have the same value of n.

#Some lines of code have been commented out; they are not necessary for the program but may be uncommented to observe flow of control.

import itertools
import gates
import SBoxConverter

#Converts a value to a truth table output column/ Boolean function.
#Values are truncated/extended to 16-bits as required.
#Returns a list of integers, not a string.
#Parameter:
#val: the decimal value to be converted.
def bitConverter(val):
    pruned = val & 0xffff
    bitString = bin(val)
    start = bitString.index('b')
    bitString = bitString[start+1:]
    ctr = 16-len(bitString)
    f = [0]*16

    for i in range(len(bitString)):
        f[ctr] = int(bitString[i])
        ctr = ctr+1
    return f

#Computes all combinations of the columns.
#Parameter:
#lst: the function, represented as a list of columns (each column is a list of 1's and 0's)
def combinations(lst):
    comboList = []
    g = gates.XOR()
    for h in range(2):
        s0 = h*lst[0]
        for i in range(2):
            s1 = g.operation([s0, i*lst[1]])[0]
            for j in range(2):
                s2 = g.operation([s1, j*lst[2]])[0]
                for k in range(2):
                    s3 = g.operation([s2, k*lst[3]])[0]
                    if h==1 or i==1 or j==1 or k==1:
                        #print(h, i, j, k)
                        #print(s0, s1, s2, s3)
                        comboList.append(s3)
    return comboList

#Returns Walsh value of a 1-output function.
#Parameter:
#val: The function, represented as a column (a list of 1's and 0's).
def walsh(val):
    f = bitConverter(val)
    #print(val, f)
    fi = []
    n = 4
    tn = (1 << n)
    #print(tn)
    cnt = 0

    for i in range(tn):
        if f[i] == 0:
            fi.append(1)
        elif f[i] == 1:
            #print(f[i])
            fi.append(-1)
        else:
            print('Error: Value Not Boolean')
            return
    #print(fi)

    for i in range(n):
        for k in range(0, tn, (1<<(i+1))):
            for j in range(k, k+(1<<i)):
                a = fi[j] + fi[j + (1 << i)]
                b = fi[j] - fi[j + (1 << i)]
                fi[j] = a
                fi[j + (1 << i)] = b

    #print(fi)
    m = fi[0]
    if m < 0:
        m = -m
    for i in range(1, tn):
        cnt = fi[i]
        if cnt < 0:
            cnt = -cnt
        if cnt > m:
            m = cnt
            
    return m

#Walsh spectrum for multi-output functions
#Calculated by taking the worst value out of all possible combinations of the columns.
#Parameter:
#lst: The list of columns.
def multiWalsh(lst):
    wList = []
    cl = combinations(lst)
    for ele in cl:
        #print(ele)
        w = walsh(ele)
        #print(w)
        wList.append(w)
    m = max(wList)
    return m

#Returns autocorrelation value of a given function.
#Parameter:
#val: The function, represented as a column (a list of 1's and 0's).
def auto(val):
    f = bitConverter(val)
    n = 4
    tn = 1<<n
    fi = []
    cnt = 0
    
    for i in range(tn):
        if f[i] == 0:
            fi.append(1)
        elif f[i] == 1:
            fi.append(-1)
        else:
            print('Error: Value Not Boolean')
            return

    for i in range(n):
        for k in range(0, tn, 1<<(i+1)):
            for j in range(k, k+(1<<i)):
                a = fi[j] + fi[j + (1<<i)]
                b = fi[j] - fi[j + (1<<i)]
                fi[j] = a
                fi[j + (1<<i)] = b

    for i in range(tn):
        fi[i] = fi[i]*fi[i]

    for i in range(n):
        for k in range(0, tn, 1<<(i+1)):
            for j in range(k, k+(1<<i)):
                a = fi[j] + fi[j + (1<<i)]
                b = fi[j] - fi[j + (1<<i)]
                fi[j] = a
                fi[j + (1<<i)] = b

    for i in range(tn):
        fi[i] = fi[i]/tn

    m = fi[1]
    if m<0:
        m = -m

    for i in range(2, tn):
        cnt = fi[i]
        if cnt<0:
            cnt = -cnt
        if cnt>m:
            m = cnt
    return int(m)

#Autocorrelation spectrum for multi-output functions.
#Parameter:
#lst: the function, represented as a list of columns.
def multiAuto(lst):
    aList = []
    cl = combinations(lst)
    for ele in cl:
        a = auto(ele)
        #print(a)
        aList.append(a)
    m = max(aList)
    return m

#Returns the hamming distance between 2 multi-output functions.
#Assumes number of outputs are the same in both.
#Parameters:
#m1, m2: The two functions to be compared to each other.
def hammingDistance(m1, m2):
    g = gates.XOR()
    if len(m1)==len(m2):
        pairs = [list(zip(m1, p)) for p in itertools.permutations(m2)]
        average = 0
        ham = []
        for i in pairs:
            h1 = 0
            for j in i:
                x = bin(g.operation([j[0], j[1]])[0])
                d = x.count('1')
                h1 = h1+d
            ham.append(h1)
        average = int(sum(ham)/len(pairs))
        return average
    else:
        return None

#Returns the number of points at which the two functions differ.
#Unlike Hamming distance, compares by elements of the corresponding SBoxes.
#Parameters:
#f1, f2: The functions to be compared (columns, in decimal format).
def outputLineChanges(f1, f2):
    ctr = 0
    sb1 = SBoxConverter.funcToSBox(f1)
    sb2 = SBoxConverter.funcToSBox(f2)
    for i in range(len(sb1)):
        if sb1[i]==sb2[i]:
            continue
        else:
            ctr = ctr+1

    return ctr
