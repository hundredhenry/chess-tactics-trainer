# cs310-project

A chess tactics training application, integrating Stockfish to create an opponent which generates tactics from the current position.

To run the program, use Python 3.12.6 and install the required packages found in requirements.lock (pip install -r requirements.lock). Then, directly run the file using 'python ./main.py'.

Alternative versions of Stockfish may need to be installed for your specific system (https://stockfishchess.org/download/), which requires editing of the filepath at the top of main.py.
stockfish-windows-x86-64-bmi2.exe works well on Intel (2013+) and AMD Zen 3+ CPUs.
stockfish-linux was compiled from source for use on kudu batch compute, but should work on the University of Warwick DCS Linux systems.