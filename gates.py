#Any 1-input or 2-input gate may be defined in this module.

#Superclass for all gates.
class LogicGate(object):
    def __init__(self, number):
        #Name.
        self.name = 'generic gate'
        #The number of inputs.
        self.__number = number

    #Get the number of inputs.
    #There is no setter method for number of inputs, only a getter, since the number of inputs to a gate cannot be changed at whim.
    def getNumber(self):
        return self.__number

    #To perform the operation required of the gate.
    #In the superclass, this operation is the identity gate, returns itself.
    #This method must be overridden by subclasses.
    def operation(self, inputlist):
        return inputlist[0]

    #Enable legible printing of the gate.
    def __str__(self):
        return self.name

    #Return 16-bit value.
    def onlyPositive(self, val):
        a = bin(val if val>0 else val+(1<<32))
        b = int(a, base=2)
        c = b & 0xffff
        return c

    #Return the Gate Equivalent (GE) for UMC library.
    def getUMCGE(self):
        return 0

#Definition for a 2-input XOR gate.
class XOR(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'xor'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)>=self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = x^y
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 2.67

#Definition for a 2-input XNOR gate.
class XNOR(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'xnor'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = ~(x^y)
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 2.0

#Definition for a NOT gate.
class NOT(LogicGate):
    def __init__(self):
        #NOT gates only take one input.
        LogicGate.__init__(self, 1)
        self.name = 'not'
        self.__number = 1

    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            x = inputlist[0]
            z = ~x
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 0.67

#Definition for a 2-input OR gate.
class OR(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'or'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)>=self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = x|y
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 1.33

#Definition for a 2-input NOR gate.
class NOR(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'nor'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = ~(x|y)
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 1.0

#Definition for a 2-input AND gate.
class AND(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'and'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            #print(inputlist)
            x = inputlist[0]
            y = inputlist[1]
            z = x&y
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 1.33

#Definition for a 2-input NAND gate.
class NAND(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'nand'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = ~(x&y)
            return [self.onlyPositive(z)]
        else:
            return None

    def getUMCGE(self):
        return 1.0

#Definition for a CNOT gate.
#The reverse of a CNOT gate is itself.
class CNOT(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'cnot'
        self.__number = 2
        
    def operation(self, inputlist):
        if len(inputlist)==self.getNumber():
            x = inputlist[0]
            y = inputlist[1]
            z = self.onlyPositive(x^y)
            ctrl = self.onlyPositive(x)
            return ([ctrl, z])
        else:
            return None

    def getUMCGE(self):
        return 2.67

#Definition for an n-variable Toffoli gate, where n is any integer greater than 2.
class TOFF(LogicGate):
    def __init__(self):
        LogicGate.__init__(self, 2)
        self.name = 'toffoli'
        self.__number = 3

    def operation(self, inputlist):
        if len(inputlist)>=self.getNumber():
            fin = inputlist[len(inputlist)-1]
            prod = [inputlist[0]]
            g1 = AND()
            for i in range(1, len(inputlist)-1):
                prod = g1.operation([prod[0], inputlist[i]])

            g2 = XOR()
            z = g2.operation([prod[0], fin])
            return inputlist[:len(inputlist)-1] + z
        else:
            return None

    def getUMCGE(self):
        return 4.0

##t = TOFF()
##n = NOT()
##cn = CNOT()
##a = 255
##b = 3855
##c = 13107
##d = 21845
##a1, b1, c1 = t.operation([255, 3855, 21845])
##d1 = n.operation([d])[0]
##a2 = a1
##d2, c2, b2 = t.operation([d1, c1, b1])
##a3 = n.operation([a2])[0]
##b3, c3, d3 = t.operation([b2, c2, d2])
##b4, a4 = cn.operation([b3, a3])
##c4, d4 = cn.operation([c3, d3])
##print(a4, b4, c4, d4)
