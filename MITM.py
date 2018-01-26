#Meet-in-the-middle version

#Currently deleting most unnecessary s-boxes in every batch for space constraints.

#Version for only reversible gates.
#The same gates every time: CNOT, Toff, NOT.

#Computes Walsh and Autocorrelation of the desired outputs and of every node generated.
#DB Contains Walsh and Autocorrelation result columns. Walsh and Autocorrelation computed for each value, even duplicates, to reduce number of DB accesses.
#If the desired s-box is not found, generates a new s-box with better Walsh and Autocorrelation values.
#Removes duplicates at each level to save time on database accesses.
#Deletes all except final two levels at each step to save storage space.

#Performs the search operations.
#Command-line arguments in order:
#Maximum depth to search till
#Maximum number of threads to use (note: the program will run at most as many concurrent processes as the number of CPU cores available)
#The S-Box to search for as space separated integers

import argparse
import logging
import sys
import os
import datetime
from multiprocessing import Process, Lock, cpu_count
import sqlite3
import itertools
#import unittest
#import sys
#import signal

import gates
import fitness
import SBoxConverter

#Create the graph object.
class Tree(object):

    lock = Lock()
    
    #Initialise a graph with gates of your choice.
    def __init__(self, md, sbox, nt, d):
        #The depth of the SBox to search for.
        self.cost = 0
        #The path to this SBox.
        self.path = ''
        #The initial values.
        self.values = []
        #Whether the node generation is happening in the forward direction or the backward direction (for meet-in-the-middle algorithm)
        self.direction = d
        #self.lastLayer = []
        self.sbox = sbox
        #The function output columns of the given SBox.
        self.outputs = SBoxConverter.sBoxToColumns(sbox)
        #The maximum allowed number of threads.
        self.numThreads = nt
        #The maximum depth to search till.
        self.maxdepth = md
        #The number of 4-output reversible functions.
        self.maxVal = self.fact(16)
        #print(self.maxdepth)
        #The depth which the circuit has achieved till now.
        self.currDepth = 0
        #The name of the SQLite database in which the results have been stored.
        self.databaseName = 'Functions.db'
        #Initialising the log file with name Progress.log.
        logging.basicConfig(filename='Progress.log',level=logging.DEBUG)
        self.rev = None
        if self.direction=='forward':
            #initial values, converted from binary.
            self.values = {'a': 255, 'b': 3855, 'c': 13107, 'd': 21845}
            self.tablename = 'NodesReversible'
        else:
            self.values = {'a': self.outputs[0], 'b': self.outputs[1], 'c': self.outputs[2], 'd': self.outputs[3]}
            self.outputs = [255, 3855, 13107, 21845]
            self.tablename = 'ReverseNodes'
        #Checking if the database already exists, i.e it has been computed upto some depth.
        self.__exists = self.checkDB()
        #print(self.tablename, self.__exists)
        if self.__exists==0:
            #print(self.direction)
            self.create(self.values)
        else:
            self.checkInOutputs()

    #Create the first layer (path will be empty, level will be 0).
    def create(self, lst):
        #print('create')
        #print(self.direction)
        #print(lst)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS '+self.tablename+' (id INTEGER PRIMARY KEY ASC, a INT NOT NULL, b INT NOT NULL, c INT NOT NULL, d INT NOT NULL, Path TEXT, Level INT NOT NULL, GE REAL NOT NULL, Walsh INT, Auto INT)')
        conn.commit()
        conn.close()
        v = [lst, '', 0, 0.0, 16, 16]
        self.addToDB([v])
        
    #Generate and automatically update a log file to keep track of progress.
    def maintainLog(self, message):
        if message[:3]=='The' or message[:6]=='System' or message[:4]=='This' or message[:9]=='Computing' or message[:4]=='Path':
            logging.info(message)
        else:
            logging.info(self.direction+': '+message)
    
    #Check if a database already exists.
    def checkDB(self):
        #print('checkDB')
        #print(self.tablename)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        tbname = self.tablename
        tbexists = 'SELECT tbl_name FROM sqlite_master WHERE type="table" AND tbl_name="'+tbname+'"'
        
        if c.execute(tbexists).fetchone():
            #print('Exists')
            self.currDepth = self.getLastLevel(self.tablename)
            self.maintainLog('This database already exists. Continuing from Level '+str(self.currDepth))
            conn.close()
            return 1

        conn.close()
        return 0

    #Add the nodes in the given list to a Database for persistent storage
    def addToDB(self, rowList):
        #print('addToDB')
        #print(self.direction)
        #print(rowList)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        for row in rowList:
            #print(row)
            if len(row)==6:
                #print(row)
                m = row[0]
                vala = m['a']
                valb = m['b']
                valc = m['c']
                vald = m['d']
                c.execute('INSERT OR REPLACE INTO '+self.tablename+' (a, b, c, d, Path, Level, GE, Walsh, Auto) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',(vala, valb, valc, vald, row[1], row[2], row[3], row[4], row[5]))    
            #else:
                #print('Error; insufficient arguments.')
                #print(row)
        conn.commit()
        conn.close()
        #self.removeDuplicates(self.tablename)

    #Retrieves values stored in the database in a previous iteration of the program.
    def getLastFromDB(self, start, end):
        #print('getLastFromDB')
        #print(self.tablename)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        values = []
        #print(self.currDepth)
        rows = c.execute('SELECT * FROM '+self.tablename+' WHERE Level=? LIMIT ? OFFSET ?',(self.currDepth-1, end, start))
        for r in rows:
            values.append(r)
        #print('Retrieved',values)
        conn.commit()
        conn.close()
        return values

    #Deletes all levels but the last two computed in each table.
    #Saves space in meet-in-the-middle algorithm.
    def keepLastTwo(self, tbname):
        conn = sqlite3.connect('Functions.db')
        c = conn.cursor()
        levels = []
        m = c.execute('SELECT DISTINCT Level FROM '+tbname+' ORDER BY Level DESC')
        for l in m:
            levels.append(l[0])
        if len(levels)>2:
            for i in levels[2:]:
                c.execute('DELETE FROM '+tbname+' WHERE Level=?', (i,))
        conn.commit()
        conn.close()
        
    #Displays the number of elements in the database.
    def getCount(self, ch):
        #print('getCount')
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        #If choice is 0, return the number of most-recently computed values.
        if ch==0:
            cnt = c.execute('SELECT COUNT(*) FROM '+self.tablename+' WHERE Level=?',(self.currDepth-1,)).fetchone()[0]
            self.maintainLog(str(cnt)+' values computed in the last iteration.')
            conn.commit()
            conn.close()
            return cnt

        #Otherwise, return the total number of reversible functions found.
        else:
            cnt = c.execute('SELECT COUNT(*) FROM '+self.tablename).fetchone()[0]
            conn.commit()
            conn.close()
            self.maintainLog(str(cnt)+' values found in total.')
            if cnt==self.maxVal:
                self.maintainLog('All reversible 4-value functions found. Exiting...')
                sys.exit()

    #Return the last computed level of the table.
    def getLastLevel(self, tbname):
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        last = c.execute('SELECT DISTINCT Level FROM '+tbname+' ORDER BY Level DESC')
        try:
            l = last.fetchone()[0]
            conn.close()
            return l
        except TypeError:
            conn.close()
            return 0
    
    #Remove duplicate functions.
    def removeDuplicates(self, tbname):
        #print('removeDuplicates')
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        r1 = c.execute('SELECT COUNT(*) FROM '+tbname).fetchone()[0]
        c.execute('DELETE FROM '+tbname+' WHERE GE NOT IN (SELECT MIN(GE) FROM '+tbname+' GROUP BY a, b, c, d)')
        c.execute('DELETE FROM '+tbname+' WHERE Level NOT IN (SELECT MIN(Level) FROM '+tbname+' GROUP BY a, b, c, d)')
        c.execute('DELETE FROM '+tbname+' WHERE id NOT IN (SELECT MIN(id) FROM '+tbname+' GROUP BY a, b, c, d)')
        r2 = c.execute('SELECT COUNT(*) FROM '+tbname).fetchone()[0]
        conn.commit()
        conn.close()
        self.maintainLog(str(r1-r2)+' of the functions were duplicates.')
            
    #Get the depth of a function from the database.
    def lvlFromDB(self, val):
        #print('lvlFromDB')
        #print(val)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        if c.execute('SELECT Level FROM '+self.tablename+' WHERE a=? AND b=? AND c=? AND d=?', (val[0], val[1], val[2], val[3])).fetchone():
            r = c.execute('SELECT Level FROM '+self.tablename+' WHERE a=? AND b=? AND c=? AND d=?', (val[0], val[1], val[2], val[3])).fetchone()
            conn.close()
            a = r[0]
            return a
        conn.close()
        return None       

    #Drops the table.
    def dropTable(self, tname):
        #print('dropTable', tname)
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        c.execute('DROP TABLE '+tname)
        conn.commit()
        conn.close()

    #To check if the desired S-Box has already been found in a previous execution
    def checkInOutputs(self):
        #print('checkInOutputs')
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        r = c.execute('SELECT Level, Path FROM '+self.tablename+' WHERE a=? AND b=? AND c=? AND d=? ORDER BY Level ASC', (self.outputs[0], self.outputs[1], self.outputs[2], self.outputs[3])).fetchone()
        if r:
            self.cost=r[0]
            self.path=r[1]
            self.outputs=[]
        conn.commit()
        conn.close()
        
    #To check if the forward direction and reverse direction have met
    def compareDirections(self):
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        #print(self.tablename)
        #print(self.rev.tablename)
        tbname = 'Common'
        outputs = self.outputs
        c.execute('CREATE TABLE IF NOT EXISTS Common(id INTEGER PRIMARY KEY ASC, a INT NOT NULL, b INT NOT NULL, c INT NOT NULL, d INT NOT NULL, Path TEXT, TotalGE REAL)')
        c.execute('INSERT INTO Common(a, b, c, d, Path, TotalGE) SELECT t1.a, t1.b, t1.c, t1.d, t1.Path||" "||t2.Path, t1.GE+t2.GE FROM '+self.tablename+' t1 JOIN '+self.rev.tablename+' t2 ON (t1.a=t2.a AND t1.b=t2.b AND t1.c=t2.c AND t1.d=t2.d)')
        #If a midpoint (for mitm algorithm) has been found.
        mindepth = c.execute('SELECT * FROM Common ORDER BY TotalGE ASC').fetchone()
        if mindepth:
            self.cost = mindepth[6]
            self.path = mindepth[5]
            outputs = []
        conn.commit()
        conn.close()
        self.outputs = outputs

    #If all the outputs have not been found, suggest alternative truth tables with equivalent or better (lower) Walsh Transformation values.
    def suggestAlternative(self):
        #print('suggestAlternative')
        conn = sqlite3.connect(self.databaseName)
        c = conn.cursor()
        w = fitness.multiWalsh(self.outputs)
        a = fitness.multiAuto(self.outputs)
        #alt = c.execute('SELECT Value, Walsh, Auto FROM '+self.tablename+' WHERE Walsh<=? AND Auto<=? ORDER BY Walsh ASC, Auto ASC, Value ASC', (w,a)).fetchone()
        alt = c.execute('SELECT * FROM '+self.tablename+' WHERE Walsh<=? AND Auto<=? ORDER BY Walsh ASC, Auto ASC, Level ASC', (w,a)).fetchone()
        if alt:
            altA = alt[1]
            altB = alt[2]
            altC = alt[3]
            altD = alt[4]
            path = alt[5]
            level = alt[6]
            ge = alt[7]
            altWalsh = alt[8]
            altAuto = alt[9]
            altSBox = SBoxConverter.funcToSBox([altA, altB, altC, altD])
            sb = 'The SBox having values '
            for ele in altSBox:
                sb = sb + str(ele)+' '
            sb = sb + ' having Gate Equivalent '+str(ge)+' and Walsh Value '+str(altWalsh)+' and Autocorrelation Value '+str(altAuto)+' may be used instead of the SBox '
            origSBox = SBoxConverter.funcToSBox(self.outputs)
            for ele in origSBox:
                sb = sb+str(ele)+' '
            sb = sb+' having and Walsh Value '+str(w)+' and Autocorrelation Value '+str(a)+'.'
            self.maintainLog(sb)
            self.maintainLog('The path to this suggested SBox is \n'+path)
        else:
            sb = 'No suitable substitute found for SBox '
            origSBox = SBoxConverter.funcToSBox(self.outputs)
            for ele in origSBox:
                sb = sb+str(ele)+' '
            sb = sb+' having Walsh Value '+str(w)+' and Autocorrelation Value '+str(a)+' within this depth.'
            self.maintainLog(sb)
        conn.commit()
        conn.close()

    #Returns False if two pairs have at least one element in common.
    def disjoint(self, p, orig):
        #print('disjoint')
        #print(p)
        #print(orig)
        chk = []
        for i in orig:
            chk.append(i)
        comp = [p[0][0][0], p[0][1][0], p[1][0][0], p[1][1][0]]
        for j in comp:
            try:
                k = chk.index(j)
                chk = chk[:k] + chk[k+1:]
            except ValueError:
                continue
        if len(chk)>0:
            return False
        else:
            return True

    #Recursively computes the factorial of a number.
    def fact(self, n):
        if n==1 or n==0:
            return 1
        else:
            return n*self.fact(n-1)

    #Flatten a list into a string.
    def flatten(self, pathList):
        strPath = ''
        for i in pathList:
            strPath = strPath+str(i)
        return strPath

    #Produces all possible combinations for a single 3-input Toffoli gate and either a NOT gate or an identity transformation.
    #Even if duplicate values are produced in a list, there is no confusion.
    def toffoliNot(self, lst, p, gequiv):
        #print('toffoliNot')
        #print(p)
        var = [[lst[0], 'a'], [lst[1], 'b'], [lst[2], 'c'], [lst[3], 'd']]
        t = gates.TOFF()
        n = gates.NOT()
        allCombos = list(itertools.permutations(var))
        #print('toffoliNot', allCombos)
        toffins = []
        #print('allcombos',allCombos)
        toffres = []
        paths = []
        ges = []
        for i in allCombos:
            #print('i', i)
            tinp = []
            for j in i[:3]:
                tinp.append(j[0])
            #tinp = list(i[:3])
            ninp = i[3][0]
            #l = enumerate(i)
            s = t.operation(tinp)
            m = n.operation([ninp])
            ge1 = gequiv + t.getUMCGE() + n.getUMCGE()
            ge2 = gequiv + t.getUMCGE()
            if self.direction=='forward':
                path1 = p + 'toffoli('+str(i[0][1])+','+str(i[1][1])+','+str(i[2][1])+'), not('+str(i[3][1])+'); '
                path2 = p + 'toffoli('+str(i[0][1])+','+str(i[1][1])+','+str(i[2][1])+'), '+str(i[3][1])+'; '
            else:
                path1 = 'toffoli('+str(i[0][1])+','+str(i[1][1])+','+str(i[2][1])+'), not('+str(i[3][1])+'); ' + p
                path2 = 'toffoli('+str(i[0][1])+','+str(i[1][1])+','+str(i[2][1])+'), '+str(i[3][1])+'; ' + p
            r1 = s + m
            r2 = s + [ninp]
            toffins.append([i[0], i[1], i[2], i[3]])
            toffres.append(r1)
            paths.append(path1)
            ges.append(ge1)
            toffins.append([i[0], i[1], i[2], i[3]])
            toffres.append(r2)
            paths.append(path2)
            ges.append(ge2)
            #print(a, b, c, d)

        #print(toffins)
        #print(lst)
        #print(toffres)
        trures = self.uncross(lst, (toffins, toffres))
        #print('trures', trures)
        withPaths = []
        for k in range(len(trures)):
            #print(paths[l])
            row = [trures[k], paths[k], ges[k]]
            withPaths.append(row)
        #print('withpaths', withPaths)
        return withPaths

    #Computes all possible outputs using 1 CNOT gate and between 0 and 2 NOT gates.
    def cnotNot(self, lst, p, gequiv):
        #print('cnotNot')
        var = [[lst[0], 'a'], [lst[1], 'b'], [lst[2], 'c'], [lst[3], 'd']]
        allPairs = list(itertools.permutations(var, 2))
        pairsOfPairs = list(itertools.permutations(allPairs, 2))
        allCombos = []
        for pop in pairsOfPairs:
            if self.disjoint(pop, lst):
                allCombos.append([list(pop[0]), list(pop[1])])
        #print('cnotnot')
        #for p in allCombos:
            #s = ''
            #for j in p:
                #for k in j:
                    #s = s+k[1]
            #print(s)
        cnotins = []
        cnotres = []
        paths = []
        ges = []
        cn = gates.CNOT()
        n = gates.NOT()
        for pair in allCombos:
            a = pair[0][0][0]
            b = pair[0][1][0]
            c = pair[1][0][0]
            d = pair[1][1][0]
            s = cn.operation([a, b])
            m = n.operation([d])[0]
            o = n.operation([c])[0]
            r1 = s + [c, d]
            ge1 = gequiv + cn.getUMCGE()
            r2 = s + [c, m]
            ge2 = gequiv + cn.getUMCGE() + n.getUMCGE()
            r3 = s + [o, d]
            ge3 = gequiv + cn.getUMCGE() + n.getUMCGE()
            r4 = s + [o, m]
            ge4 = gequiv + cn.getUMCGE() + n.getUMCGE() + n.getUMCGE()
            if self.direction=='forward':
                path1 = p + 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), '+str(pair[1][0][1])+', '+str(pair[1][1][1])+'; '
                path2 = p + 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), '+str(pair[1][0][1])+', not('+str(pair[1][1][1])+'); '
                path3 = p + 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), not('+str(pair[1][0][1])+'), '+str(pair[1][1][1])+'; '
                path4 = p + 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), not('+str(pair[1][0][1])+'), not('+str(pair[1][1][1])+'); '
            else:
                path1 = 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), '+str(pair[1][0][1])+', '+str(pair[1][1][1])+'; ' + p
                path2 = 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), '+str(pair[1][0][1])+', not('+str(pair[1][1][1])+'); ' + p
                path3 = 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), not('+str(pair[1][0][1])+'), '+str(pair[1][1][1])+'; ' + p
                path4 = 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), not('+str(pair[1][0][1])+'), not('+str(pair[1][1][1])+'); ' + p
            cnotins.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            cnotres.append(r1)
            ges.append(ge1)
            paths.append(path1)
            cnotins.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            cnotres.append(r2)
            ges.append(ge2)
            paths.append(path2)
            cnotins.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            cnotres.append(r3)
            ges.append(ge3)
            paths.append(path3)
            cnotins.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            cnotres.append(r4)
            ges.append(ge4)
            paths.append(path4)
            
        trures = self.uncross(lst, (cnotins, cnotres))
        withPaths = []
        for k in range(len(trures)):
            row = [trures[k], paths[k], ges[k]]
            withPaths.append(row)
	#print(cnotins)
        return withPaths
        
    #Computes all possible ways of combining a list of inputs into 2 2-input CNOT gates.
    def twoCNOT(self, lst, p, gequiv):
        #print('twoCNOT')
        var = [[lst[0], 'a'], [lst[1], 'b'], [lst[2], 'c'], [lst[3], 'd']]
        allPairs = list(itertools.permutations(var, 2))
        pairsOfPairs = list(itertools.combinations(allPairs, 2))
        allCombos = []
        for pop in pairsOfPairs:
            if self.disjoint(pop, lst):
                allCombos.append([list(pop[0]), list(pop[1])])
        #print('twocnot', allCombos)
        combos = []
        twores = []
        ges = []
        paths = []
        cn = gates.CNOT()
        for pair in allCombos:
            a = pair[0][0][0]
            b = pair[0][1][0]
            c = pair[1][0][0]
            d = pair[1][1][0]
            r1 = cn.operation([a, b])
            r2 = cn.operation([c, d])
            res = r1 + r2
            ge = gequiv + 2*(cn.getUMCGE())
            if self.direction=='forward':
                path = p + 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), cnot('+str(pair[1][0][1])+','+str(pair[1][1][1])+'); '
            else:
                path = 'cnot('+str(pair[0][0][1])+','+str(pair[0][1][1])+'), cnot('+str(pair[1][0][1])+','+str(pair[1][1][1])+'); ' + p
            combos.append([pair[0][0], pair[0][1], pair[1][0], pair[1][1]])
            twores.append(res)
            paths.append(path)
            ges.append(ge)
        #print(combos)
        trures = self.uncross(lst, (combos, twores))
        withPaths = []
        for k in range(len(trures)):
            row = [trures[k], paths[k], ges[k]]
            withPaths.append(row)
        return withPaths
    
    #Generates all outputs of a list using only NOT and identity transformations.
    def notIdentity(self, bus, p, gequiv):
        #print('notIdentity')
        combos = []
        res = []
        paths = []
        ges = []
        n = gates.NOT()
        s = len(bus)
        nd = 2**s
        alpha = ['a', 'b', 'c', 'd']
        for i in range(nd):
            ge = gequiv
            c = SBoxConverter.bitExtended(i, s)
            r = []
            path = p
            newPath = ''
            for j in range(s):
                if c[j]=='0':
                    r.append(n.operation([bus[j]])[0])
                    newPath = newPath + 'not(' + alpha[j] + '), '
                    ge = ge + n.getUMCGE()
                else:
                    r.append(bus[j])
                    newPath = newPath + alpha[j] + ', '
            newPath = newPath[:len(newPath)-2] + '; '
            if self.direction=='forward':
                path = path+newPath
            else:
                path = newPath+path
            combos.append(bus)
            mappedR = {'a':r[0], 'b':r[1], 'c':r[2], 'd':r[3]}
            res.append([mappedR, path, ge])
            #print(c, r)
        return res        

    #Uncrosses the wires.
    #Works even if repetitions occur.
    def uncross(self, lst, scrambled):
        combos = scrambled[0]
        res = scrambled[1]
        uncrossed = []
        for i in range(len(combos)):
            unscrambled = dict()
            for j in range(len(combos[i])):
                #print('combos[i]', combos[i])
                #print(res[i])
                unscrambled[combos[i][j][1]] = res[i][j]
            #print(unscrambled)
            uncrossed.append(unscrambled)
        #print('uncrossed', uncrossed)
        return uncrossed
        #print(c, r, uncrossed[i])
   
    #To apply the gate on as many inputs as required and return the 16-bit output.
    def applyGates(self, lst, eP, ege):
        #print('applyGates')
        finres = []
        rtoff = self.toffoliNot(lst, eP, ege)
        finres = finres + rtoff
        #print('Toffoli done.')
        #print(len(finres))
        r1cnot = self.cnotNot(lst, eP, ege)
        finres = finres + r1cnot
        #print('Single CNOT done.')
        #print(len(finres))
        r2cnot = self.twoCNOT(lst, eP, ege)
        finres = finres + r2cnot
        #print('Double CNOT done.')
        #print(len(finres))
        noti = self.notIdentity(lst, eP, ege)
        finres = finres + noti
        #print('All done')
	#print(len(finres))
        for i in range(len(finres)):
            e = finres[i][0]
            fn = list(e.values())
            try:
                w = fitness.multiWalsh(fn)
                au = fitness.multiAuto(fn)
                finres[i] = finres[i] + [w, au]
            except TypeError:
                print(i)
                print(e)
        #for f in finres:
            #print(f)
        #print(len(finres))
        return finres

    #The task to be executed by each Process.
    def compute(self, l, index, limit):
        global lock
        #print('compute')
        #print(self.direction)
        #print(self.tablename)
        #l = args[0]
        #print(l)
        lock.acquire()
        parentList = self.getLastFromDB(index, limit)
        #print(parentList)
        lock.release()
        #print(parentList)
        lastLayer = []
        #pairs = args[1]
        #print(pairs)
        #print(list(parentList)[0])
        for lst in parentList:
            parents = lst[1:5]
            existingPath = lst[5]
            level = lst[6] + 1
            ge = lst[7]
            r = self.applyGates(parents, existingPath, ge)
            for i in r:
                row = i[:2] + [level] + i[2:]
                lastLayer.append(row)
        #print(lastLayer[0])
        lock.acquire()
        self.addToDB(lastLayer)
        self.maintainLog(str(len(lastLayer))+' functions computed from functions between '+str(index)+' and '+str(index+limit)+'.')
        self.removeDuplicates(self.tablename)
        #self.compareDirections()
        lock.release()
        
    #Generate new layers of the graph
    def generate(self):
        global lock
        lock = Lock()
        self.rev = Tree(self.maxdepth, self.sbox, self.numThreads, 'backwards')
        #print(self.rev.values)
        index = 0
        limit = 5000
        end = index + limit
        pairs = []
        self.currDepth = self.currDepth+1
        self.rev.currDepth = self.rev.currDepth+1
        midpoint = int(self.maxdepth/2) + (self.maxdepth%2)

        #self.checkInOutputs()

        #continue producing outputs until maximum cost is reached or all outputs are found.
        while (self.currDepth+self.rev.currDepth) <=self.maxdepth and len(self.outputs)>0:
        #while self.currDepth <=self.maxdepth and len(self.outputs)>0:
            self.maintainLog('Computing layer at depth '+str(self.currDepth)+'...')
            self.maintainLog('System time is '+str(datetime.datetime.now()))
            #Delete all levels but the last 2 from the database to preserve space.
            self.keepLastTwo(self.tablename)
            self.keepLastTwo(self.rev.tablename)
            ctr = 0
            nt = 0
            proc = []
            numParents = self.getCount(0)
            #print('Last computed:',numParents)
            #Keep iterating until all pairs in the database have been retrieved and processed.
            while index<=numParents:
                if nt<self.numThreads-1 and nt<(cpu_count()):
                    p1 = Process(target=self.compute, args=(lock, index, limit))
                    p1.start()
                    p2 = Process(target=self.rev.compute, args=(lock, index, limit))
                    p2.start()
                    proc.append(p1)
                    proc.append(p2)
                    #Increment the index.
                    nt = nt+2
                    index = end
                    end = end + limit
                else:
                    proc[0].join()
                    nt = nt-1
                    proc = proc[1:]
                    #for p in proc:
                        #p.join()
                    #nt = 0

            for p in proc:
                p.join()

            self.maintainLog('Completed processing of '+str(numParents)+' functions.')
            self.maintainLog('System time is '+str(datetime.datetime.now()))
            #Reset the values.
            index = 0
            end = index + limit
            #self.removeDuplicates(self.tablename)
            #self.rev.removeDuplicates(self.rev.tablename)
            #self.getCount(0)
            self.getCount(1)
            #Increment the depth.
            self.currDepth = self.currDepth+1
            self.rev.currDepth = self.rev.currDepth+1
	    #Check if the outputs have been found this time.
            self.compareDirections()

	#If the SBox could not be generated with these gates and within these depth constraints, add it to the log file.
        if len(self.outputs)>0:
            self.maintainLog('Maximum depth reached but required SBox not found.')
            self.suggestAlternative()

        #If the SBox was found store the cost and path of the outputs.
        else:
            self.maintainLog('The SBox was found at depth '+str(self.cost))
            self.maintainLog('Path is '+self.path)

	#Delete all the common values and the reverse direction so that the generated nodes can be used again for a different SBox.
        #Only delete at the beginning if this SBox is different from the old SBox.
        #self.dropTable('Common')
        #self.dropTable(self.rev.tablename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('depth', nargs = 1, help='store the maximum depth to check till')
    parser.add_argument('threads', nargs = 1, help='store the maximum number of threads to use')
    parser.add_argument('outputs', nargs = '+', help='store the desired s-box as space-separated integers')

    #parser.add_argument('unittest_args', nargs='*')
    args = parser.parse_args()
    numthreads = args.threads
    maxdepth = args.depth
    o = args.outputs
    for i in range(len(o)):
        o[i] = int(o[i])

    t = Tree(int(maxdepth[0]), o, int(numthreads[0]), 'forward')
    t.generate()
