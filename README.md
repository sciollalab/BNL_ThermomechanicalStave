# BNL_ThermomechanicalStave
LabVIEW code for the ATLAS ITk thermomechanical stave assembly at Brookhaven National Lab

The purpose of this LabVIEW code is to assemble staves from their constituent stave cores and modules at Brookhaven National Laboratory (BNL). 
The code operates an XYZ stage and camera, running calibration, placement, and final survey phases, to coordinate mounting modules on the stave core. We group tasks thematically to smooth and organize the user's workflow. The code is also modular to facilitate step-oriented development and optimization. Each component is intended to operate in both standalone and integrated modes. The code automatically tracks the completion status of the current stave.

Code built on LabVIEW 2016.

Required LabVIEW software packages: 
- LabVIEW Full Development System 
- NI Vision VAS 2016
- NI Vision VDM 2016
