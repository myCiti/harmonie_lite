from machine import Pin, I2C
from machine_i2c_lcd import I2cLcd
from micropython import const
from collections import OrderedDict
from gc import collect
import time

TIMERS = OrderedDict(
    Open = const(3),
    Close = const(3),
    MidStop = const(14)
)

### input/output pins
iPins = {
    'Open'      : 4,
    'Close'     : 5,
    'Stop'      : 6,
    'OpenLmt'   : 3, 
    'CloseLmt'  : 2,
}

oPins = {
    'Open'      : 10,
    'Close'     : 11,
    'Stop'      : 12,
}

Input = dict((name, Pin(pin, Pin.IN, Pin.PULL_DOWN)) for (name, pin) in iPins.items())
Output = dict((name, Pin(pin, Pin.OUT, Pin.PULL_DOWN)) for (name, pin) in oPins.items())

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400_000)
lcd = I2cLcd(i2c, 0x27, 4, 20)

### Global variables
n_reads = 10
readpin_delay = const(50)
writepin_delay = const(150)
is_running = False

def readPin(pin, n_times=n_reads):
    counter = 0

    for _ in range(n_times):
        if Input[pin].value():
            counter += 1
        time.sleep_us(readpin_delay)
    
    if counter == n_times:
        return True
    
    return False

def writePin(pin, delay = writepin_delay):
    if not readPin('Stop'):
        if pin == 'Open' and not readPin('OpenLmt'):
            Output[pin].high()
        elif pin == 'Close' and not readPin('CloseLmt'):
            Output[pin].high()
        else:
            Output[pin].high()
        
        time.sleep_ms(delay)
        Output[pin].low()

def count_down(duration):

    for i in range(duration, 0, -1):
        start = time.ticks_ms()
        lcd.write_line(f'{i:>3}', 1, 18)
        if readPin('Stop'): break
        elapsed = time.ticks_diff(time.ticks_ms(), start)
        time.sleep_ms(1000 - elapsed)

def initialize():
    global is_running 
    
    is_running = False
    
    for p in Output:
        Output[p].low()

    lcd.clear()
    for l, (k,v) in enumerate(TIMERS.items()):
        lcd.write_line(f'{k.upper():<10}: {v:>3}', l+1, 1)
    
    time.sleep_ms(500)
    
def main_logic():

    global is_running 
    
    is_running = True
    from_midstop_to_open = False
    door_state = 0

    lcd.clear()
    while not readPin('Stop'):
        if door_state == 0:
            if readPin('Close') and not readPin('CloseLmt'):
                writePin('Close')
                lcd.write_line_center('FERMER', 1)
                door_state = 1
            elif readPin('Open') and not readPin('OpenLmt'):
                writePin('Open') 
                lcd.write_line_center('OUVRIR', 1)
                door_state = 2

        elif door_state == 1:
            if readPin('CloseLmt'):
                lcd.write_line_center('PORTE FERMEE', 1)
                count_down(TIMERS['Close'])
                writePin('Open')
                lcd.write_line_center('OUVRIR', 1)
                door_state = 2
                collect()

        elif door_state == 2:
            if readPin('OpenLmt'):
                lcd.write_line_center('PORTE OUVERTE', 1)
                count_down(TIMERS['Open'])
                writePin('Close')
                if TIMERS['MidStop'] > 0 and not from_midstop_to_open:
                    lcd.write_line_center('MI-ARRET', 1)
                    door_state = 3
                else:
                    lcd.write_line_center('FERMER', 1)
                    from_midstop_to_open = False
                    door_state = 1
                collect()

        elif door_state == 3:
                count_down(TIMERS['MidStop'])
                writePin('Open')
                lcd.write_line_center('OUVRIR', 1)
                from_midstop_to_open = True
                door_state = 2
                collect()
        else:
            door_state = 0
        
        time.sleep_ms(10)

def main():
    initialize()
    
    while True:
        if not is_running:
            if (readPin('Close') or readPin('Open')) and not Output['Stop'].value():
                main_logic()
            
            if readPin('Stop'):
                initialize()

            time.sleep_ms(50)           

if __name__ == '__main__':
    main()
