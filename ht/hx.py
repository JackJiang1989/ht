# -*- coding: utf-8 -*-
'''Chemical Engineering Design Library (ChEDL). Utilities for process modeling.
Copyright (C) 2016, Caleb Bell <Caleb.Andrew.Bell@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''

from __future__ import division
from math import exp, log, floor, sqrt
from math import tanh # 1/coth
from scipy.interpolate import interp1d
from scipy.optimize import ridder 
from fluids.piping import BWG_integers, BWG_inch, BWG_SI
from pprint import pprint
TEMA_R_to_metric = 0.17611018

__all__ = ['effectiveness_from_NTU', 'NTU_from_effectiveness', 'calc_Cmin',
'calc_Cmax', 'calc_Cr',
'NTU_from_UA', 'UA_from_NTU', 'effectiveness_NTU_method', 'F_LMTD_Fakheri', 
'temperature_effectiveness_basic', 'temperature_effectiveness_TEMA_J',
'temperature_effectiveness_TEMA_H',
'check_tubing_TEMA', 'get_tube_TEMA',
'DBundle_min', 'shell_clearance', 'baffle_thickness', 'D_baffle_holes',
'L_unsupported_max', 'Ntubes_Perrys', 'Ntubes_VDI', 'Ntubes_Phadkeb',
'Ntubes_HEDH', 'Ntubes', 'D_for_Ntubes_VDI', 'TEMA_heads', 'TEMA_shells', 
'TEMA_rears', 'TEMA_services', 'baffle_types']


# TODO: Implement selection algorithms for heat exchangers from
# Systematic Procedure for Selection of Heat Exchangers
# 10.1243/PIME_PROC_1983_197_006_02


def effectiveness_from_NTU(NTU, Cr, subtype='counterflow'):
    r'''Returns the effectiveness of a heat exchanger at a specified heat 
    capacity rate, number of transfer units, and configuration. The following
    configurations are supported:
        
        * Counterflow (ex. double-pipe)
        * Parallel (ex. double pipe inefficient configuration)
        * Shell and tube exchangers with even numbers of tube passes,
          one or more shells in series
        * Crossflow, single pass, fluids unmixed
        * Crossflow, single pass, Cmax mixed, Cmin unmixed
        * Crossflow, single pass, Cmin mixed, Cmax unmixed
        * Boiler or condenser
    
    These situations are normally not those which occur in real heat exchangers,
    but are useful for academic purposes. More complicated expressions are 
    available for other methods. These equations are confirmed in [1]_,
    [2]_, and [3]_.
    
    For parallel flow heat exchangers:

    .. math::
        \epsilon = \frac{1 - \exp[-NTU(1+C_r)]}{1+C_r}

    For counterflow heat exchangers:

    .. math::
        \epsilon = \frac{1 - \exp[-NTU(1-C_r)]}{1-C_r\exp[-NTU(1-C_r)]},\; C_r < 1

        \epsilon = \frac{NTU}{1+NTU},\; C_r = 1

    For TEMA E shell-and-tube heat exchangers with one shell pass, 2n tube 
    passes:

    .. math::
        \epsilon_1 = 2\left\{1 + C_r + \sqrt{1+C_r^2}\times\frac{1+\exp
        [-(NTU)_1\sqrt{1+C_r^2}]}{1-\exp[-(NTU)_1\sqrt{1+C_r^2}]}\right\}^{-1}

    For TEMA E shell-and-tube heat exchangers with more than one shell pass, 2n  
    tube passes (this model assumes each exchanger has an equal share of the 
    overall NTU or said more plainly, the same UA):

    .. math::
        \epsilon = \left[\left(\frac{1-\epsilon_1 C_r}{1-\epsilon_1}\right)^2
        -1\right]\left[\left(\frac{1-\epsilon_1 C_r}{1-\epsilon_1}\right)^n
        - C_r\right]^{-1}

    For cross-flow (single-pass) heat exchangers with both fluids unmixed:

    .. math::
        \epsilon = 1 - \exp\left[\left(\frac{1}{C_r}\right)
        (NTU)^{0.22}\left\{\exp\left[C_r(NTU)^{0.78}\right]-1\right\}\right]

    For cross-flow (single-pass) heat exchangers with Cmax mixed, Cmin unmixed:

    .. math::
        \epsilon = \left(\frac{1}{C_r}\right)(1 - \exp\left\{-C_r[1-\exp(-NTU)]\right\})

    For cross-flow (single-pass) heat exchangers with Cmin mixed, Cmax unmixed:

    .. math::
        \epsilon = 1 - \exp(-C_r^{-1}\{1 - \exp[-C_r(NTU)]\})

    For cases where `Cr` = 0, as in an exchanger with latent heat exchange,
    flow arrangement does not matter: 

    .. math::
        \epsilon = 1 - \exp(-NTU)

    Parameters
    ----------
    NTU : float
        Thermal Number of Transfer Units [-]
    Cr : float
        The heat capacity rate ratio, of the smaller fluid to the larger
        fluid, [-]
    subtype : str, optional
        The subtype of exchanger; one of 'counterflow', 'parallel', 'crossflow'
        'crossflow, mixed Cmin', 'crossflow, mixed Cmax', 'boiler', 'condenser',
        'S&T', or 'nS&T' where n is the number of shell and tube exchangers in 
        a row

    Returns
    -------
    effectiveness : float
        The thermal effectiveness of the heat exchanger, [-]

    Notes
    -----
    Once the effectiveness of the exchanger has been calculated, the total
    heat transfered can be calculated according to the following formulas,
    depending on which stream temperatures are known:
        
    If the inlet temperatures for both sides are known:
        
    .. math::
        Q=\epsilon C_{min}(T_{h,i}-T_{c,i})
        
    If the outlet temperatures for both sides are known:
        
    .. math::
        Q = \frac{\epsilon C_{min}C_{hot}C_{cold}(T_{c,o}-T_{h,o})}
        {\epsilon  C_{min}(C_{hot} +C_{cold}) - (C_{hot}C_{cold}) }
    
    If the hot inlet and cold outlet are known:
        
    .. math::
        Q = \frac{\epsilon C_{min}C_c(T_{co}-T_{hi})}{\epsilon C_{min}-C_c}
        
    If the hot outlet stream and cold inlet stream are known:
        
    .. math::
        Q = \frac{\epsilon C_{min}C_h(T_{ci}-T_{ho})}{\epsilon C_{min}-C_h}
    
    
    If the inlet and outlet conditions for a single side are known, the
    effectiveness wasn't needed for it to be calculated. For completeness,
    the formulas are as follows:
        
    .. math::
        Q = C_c(T_{c,o} - T_{c,i}) = C_h(T_{h,i} - T_{h,o})
        
    There is also a term called :math:`Q_{max}`, which is the heat which would
    have been transfered if the effectiveness was 1. It is calculated as
    follows:
        
    .. math::
        Q_{max} = \frac{Q}{\text{effectiveness}}
        
    Examples
    --------
    Worst case, parallel flow:
    
    >>> effectiveness_from_NTU(NTU=5, Cr=0.7, subtype='parallel')
    0.5881156068417585
    
    Crossflow, somewhat higher effectiveness:
        
    >>> effectiveness_from_NTU(NTU=5, Cr=0.7, subtype='crossflow')
    0.8444804481910532

    Counterflow, better than either crossflow or parallel flow:

    >>> effectiveness_from_NTU(NTU=5, Cr=0.7, subtype='counterflow')
    0.9206703686051108
    
    One shell and tube heat exchanger gives worse performance than counterflow,
    but they are designed to be economical and compact which a counterflow
    exchanger would not be. As the number of shells approaches infinity,
    the counterflow result is obtained exactly.
    
    >>> effectiveness_from_NTU(NTU=5, Cr=0.7, subtype='S&T')
    0.6834977044311439
    >>> effectiveness_from_NTU(NTU=5, Cr=0.7, subtype='50S&T')
    0.9205058702789254

    
    Overall case of rating an existing heat exchanger where a known flowrate
    of steam and oil are contacted in crossflow, with the steam side mixed
    (example 10-9 in [3]_):
        
    >>> U = 275 # W/m^2/K
    >>> A = 10.82 # m^2
    >>> Cp_oil = 1900 # J/kg/K
    >>> Cp_steam = 1860 # J/kg/K
    >>> m_steam = 5.2 # kg/s
    >>> m_oil = 0.725 # kg/s
    >>> Thi = 130 # °C
    >>> Tci = 15 # °C
    >>> Cmin = calc_Cmin(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> Cmax = calc_Cmax(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> Cr = calc_Cr(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> NTU = NTU_from_UA(UA=U*A, Cmin=Cmin)
    >>> eff = effectiveness_from_NTU(NTU=NTU, Cr=Cr, subtype='crossflow, mixed Cmax')
    >>> Q = eff*Cmin*(Thi - Tci)
    >>> Tco = Tci + Q/(m_oil*Cp_oil)
    >>> Tho = Thi - Q/(m_steam*Cp_steam)
    >>> Cmin, Cmax, Cr
    (1377.5, 9672.0, 0.14242142266335814)
    >>> NTU, eff, Q
    (2.160072595281307, 0.8312180361425988, 131675.32715043944)
    >>> Tco, Tho
    (110.59007415639887, 116.38592564614977)
    
    Alternatively, if only the outlet temperatures had been known:
        
    >>> Tco = 110.59007415639887
    >>> Tho = 116.38592564614977
    >>> Cc, Ch = Cmin, Cmax # In this case but not always
    >>> Q = eff*Cmin*Cc*Ch*(Tco - Tho)/(eff*Cmin*(Cc+Ch) - Ch*Cc)
    >>> Thi = Tho + Q/Ch
    >>> Tci = Tco - Q/Cc
    >>> Q, Tci, Thi
    (131675.32715043964, 14.999999999999858, 130.00000000000003)



    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    .. [2] Shah, Ramesh K., and Dusan P. Sekulic. Fundamentals of Heat 
       Exchanger Design. 1st edition. Hoboken, NJ: Wiley, 2002.
    .. [3] Holman, Jack. Heat Transfer. 10th edition. Boston: McGraw-Hill 
       Education, 2009.
    '''
    if Cr > 1:
        raise Exception('Heat capacity rate must be less than 1 by definition.')
        
    if subtype == 'counterflow':
        if Cr < 1:
            return (1. - exp(-NTU*(1. - Cr)))/(1. - Cr*exp(-NTU*(1. - Cr)))
        elif Cr == 1:
            return NTU/(1. + NTU)
    elif subtype == 'parallel':
            return (1. - exp(-NTU*(1. + Cr)))/(1. + Cr)
    elif 'S&T' in subtype:
        str_shells = subtype.split('S&T')[0]
        shells = int(str_shells) if str_shells else 1
        NTU = NTU/shells
        
        top = 1. + exp(-NTU*(1. + Cr**2)**.5)
        bottom = 1. - exp(-NTU*(1. + Cr**2)**.5)
        effectiveness = 2./(1. + Cr + (1. + Cr**2)**.5*top/bottom)
        if shells > 1:
            term = ((1. - effectiveness*Cr)/(1. - effectiveness))**shells
            effectiveness = (term - 1.)/(term - Cr)
        return effectiveness
    
    elif subtype == 'crossflow':
        return 1. - exp(1./Cr*NTU**0.22*(exp(-Cr*NTU**0.78) - 1.))
    elif subtype == 'crossflow, mixed Cmin':
        return 1. -exp(-Cr**-1*(1. - exp(-Cr*NTU)))
    elif subtype ==  'crossflow, mixed Cmax':
        return (1./Cr)*(1. - exp(-Cr*(1. - exp(-NTU))))
    elif subtype in ['boiler', 'condenser']:
        return  1. - exp(-NTU)
    else:
        raise Exception('Input heat exchanger type not recognized')
        

def NTU_from_effectiveness(effectiveness, Cr, subtype='counterflow'):
    r'''Returns the Number of Transfer Units of a heat exchanger at a specified 
    heat capacity rate, effectiveness, and configuration. The following
    configurations are supported:
        
        * Counterflow (ex. double-pipe)
        * Parallel (ex. double pipe inefficient configuration)
        * Shell and tube exchangers with even numbers of tube passes,
          one or more shells in series (TEMA E (one pass shell) only)
        * Crossflow, single pass, fluids unmixed
        * Crossflow, single pass, Cmax mixed, Cmin unmixed
        * Crossflow, single pass, Cmin mixed, Cmax unmixed
        * Boiler or condenser

    These situations are normally not those which occur in real heat exchangers,
    but are useful for academic purposes. More complicated expressions are 
    available for other methods. These equations are confirmed in [1]_, [2]_,
    and [3]_.
    
    For parallel flow heat exchangers:

    .. math::
        NTU = -\frac{\ln[1 - \epsilon(1+C_r)]}{1+C_r}
        
    For counterflow heat exchangers:

    .. math::
        NTU = \frac{1}{C_r-1}\ln\left(\frac{\epsilon-1}{\epsilon C_r-1}\right)
        
        NTU = \frac{\epsilon}{1-\epsilon} \text{ if } C_r = 1

    For TEMA E shell-and-tube heat exchangers with one shell pass, 2n tube 
    passes:

    .. math::
        (NTU)_1 = -(1 + C_r^2)^{-0.5}\ln\left(\frac{E-1}{E+1}\right)
        
        E = \frac{2/\epsilon_1 - (1 + C_r)}{(1 + C_r^2)^{0.5}}

    For TEMA E shell-and-tube heat exchangers with more than one shell pass, 2n  
    tube passes (this model assumes each exchanger has an equal share of the 
    overall NTU or said more plainly, the same UA):

    .. math::
        \epsilon_1 = \frac{F-1}{F-C_r}
        
        F = \left(\frac{\epsilon C_r-1}{\epsilon-1}\right)^{1/n}
        
        NTU = n(NTU)_1
        
    For cross-flow (single-pass) heat exchangers with both fluids unmixed, 
    there is no analytical solution. However, the function is monotonically
    increasing, and a closed-form solver is implemented, guaranteed to solve
    for :math:`10^{-7} < NTU < 10^5`.

    For cross-flow (single-pass) heat exchangers with Cmax mixed, Cmin unmixed:

    .. math::
        NTU = -\ln\left[1 + \frac{1}{C_r}\ln(1 - \epsilon C_r)\right]
        
    For cross-flow (single-pass) heat exchangers with Cmin mixed, Cmax unmixed:

    .. math::
        NTU = -\frac{1}{C_r}\ln[C_r\ln(1-\epsilon)+1]

    For cases where `Cr` = 0, as in an exchanger with latent heat exchange,
    flow arrangement does not matter: 

    .. math::
        NTU = -\ln(1-\epsilon)

    Parameters
    ----------
    effectiveness : float
        The thermal effectiveness of the heat exchanger, [-]
    Cr : float
        The heat capacity rate ratio, of the smaller fluid to the larger
        fluid, [-]
    subtype : str, optional
        The subtype of exchanger; one of 'counterflow', 'parallel', 'crossflow'
        'crossflow, mixed Cmin', 'crossflow, mixed Cmax', 'boiler', 'condenser',
        'S&T', or 'nS&T' where n is the number of shell and tube exchangers in 
        a row

    Returns
    -------
    NTU : float
        Thermal Number of Transfer Units [-]

    Notes
    -----
    Unlike :obj:`ht.hx.effectiveness_from_NTU`, not all inputs can 
    calculate the NTU - many exchanger types have effectiveness limits
    below 1 which depend on `Cr` and the number of shells in the case of
    heat exchangers. If an impossible input is given, an error will be raised
    and the maximum possible effectiveness will be printed.
    
    >>> NTU_from_effectiveness(.99, Cr=.7, subtype='5S&T')
    Traceback (most recent call last):
    Exception: The specified effectiveness is not physically possible for this configuration; the maximum effectiveness possible is 0.974122977755.

    Examples
    --------
    Worst case, parallel flow:
    
    >>> NTU_from_effectiveness(effectiveness=0.5881156068417585, Cr=0.7, subtype='parallel')
    5.000000000000012
    
    Crossflow, somewhat higher effectiveness:
        
    >>> NTU_from_effectiveness(effectiveness=0.8444804481910532, Cr=0.7, subtype='crossflow')
    5.000000000000001

    Counterflow, better than either crossflow or parallel flow:

    >>> NTU_from_effectiveness(effectiveness=0.9206703686051108, Cr=0.7, subtype='counterflow')
    5.0
    
    Shell and tube exchangers:
    
    >>> NTU_from_effectiveness(effectiveness=0.6834977044311439, Cr=0.7, subtype='S&T')
    5.000000000000071
    >>> NTU_from_effectiveness(effectiveness=0.9205058702789254, Cr=0.7, subtype='50S&T')
    4.999999999999996


    Overall case of rating an existing heat exchanger where a known flowrate
    of steam and oil are contacted in crossflow, with the steam side mixed,
    known inlet and outlet temperatures, and unknown UA
    (based on example 10-8 in [3]_):

    >>> Cp_oil = 1900 # J/kg/K
    >>> Cp_steam = 1860 # J/kg/K
    >>> m_steam = 5.2 # kg/s
    >>> m_oil = 1.45 # kg/s
    >>> Thi = 130 # °C
    >>> Tci = 15 # °C
    >>> Tco = 85 # °C # Design specification
    >>> Q = Cp_oil*m_oil*(Tci-Tco)
    >>> dTh = Q/(m_steam*Cp_steam)
    >>> Tho = Thi + dTh
    >>> Cmin = calc_Cmin(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> Cmax = calc_Cmax(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> Cr = calc_Cr(mh=m_steam, mc=m_oil, Cph=Cp_steam, Cpc=Cp_oil)
    >>> effectiveness = -Q/Cmin/(Thi-Tci)
    >>> NTU = NTU_from_effectiveness(effectiveness, Cr, subtype='crossflow, mixed Cmax')
    >>> UA = UA_from_NTU(NTU, Cmin)
    >>> U = 200 # Assume this was calculated; would actually need to be obtained iteratively as U depends on the exchanger geometry
    >>> A = UA/U
    >>> Tho, Cmin, Cmax, Cr
    (110.06100082712986, 2755.0, 9672.0, 0.2848428453267163)
    >>> effectiveness, NTU, UA, A
    (0.6086956521739131, 1.1040839095588, 3041.751170834494, 15.208755854172471)

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    .. [2] Shah, Ramesh K., and Dusan P. Sekulic. Fundamentals of Heat 
       Exchanger Design. 1st edition. Hoboken, NJ: Wiley, 2002.
    .. [3] Holman, Jack. Heat Transfer. 10th edition. Boston: McGraw-Hill 
       Education, 2009.
    '''
    if Cr > 1:
        raise Exception('Heat capacity rate must be less than 1 by definition.')

    if subtype == 'counterflow':
        # [2]_ gives the expression 1./(1-Cr)*log((1-Cr*eff)/(1-eff)), but
        # this is just the same equation rearranged differently.
        if Cr < 1:
            return 1./(Cr - 1.)*log((effectiveness - 1.)/(effectiveness*Cr - 1.))
        elif Cr == 1:
            return effectiveness/(1. - effectiveness)
    elif subtype == 'parallel':
        if effectiveness*(1. + Cr) > 1:
            raise Exception('The specified effectiveness is not physically \
possible for this configuration; the maximum effectiveness possible is %s.' % (1./(Cr + 1.)))
        return -log(1. - effectiveness*(1. + Cr))/(1. + Cr)
    elif 'S&T' in subtype:
        # [2]_ gives the expression
        # D = (1+Cr**2)**0.5
        # 1/D*log((2-eff*(1+Cr-D))/(2-eff*(1+Cr + D)))
        # This is confirmed numerically to be the same equation rearranged
        # differently
        str_shells = subtype.split('S&T')[0]
        shells = int(str_shells) if str_shells else 1
        
        F = ((effectiveness*Cr - 1.)/(effectiveness - 1.))**(1/shells)
        e1 = (F - 1.)/(F - Cr)
        E = (2./e1 - (1. + Cr))/(1. + Cr**2)**0.5
        
        if (E - 1.)/(E + 1.) <= 0:
            # Derived with SymPy
            max_effectiveness = (-((-Cr + sqrt(Cr**2 + 1) + 1)/(Cr + sqrt(Cr**2 + 1) - 1))**shells + 1)/(Cr - ((-Cr + sqrt(Cr**2 + 1) + 1)/(Cr + sqrt(Cr**2 + 1) - 1))**shells)
            raise Exception('The specified effectiveness is not physically \
possible for this configuration; the maximum effectiveness possible is %s.' % (max_effectiveness))
        
        NTU = -(1 + Cr**2)**-0.5*log((E - 1.)/(E + 1.))
        return shells*NTU
    
    elif subtype == 'crossflow':
        # This will fail if NTU is more than 10,000 or less than 1E-7, but
        # this is extremely unlikely to occur in normal usage.
        # Maple and SymPy and Wolfram Alpha all failed to obtain an exact
        # analytical expression even with coefficients for 0.22 and 0.78 or 
        # with an explicit value for Cr. The function has been plotted,
        # and appears to be monotonic - there is only one solution.
        def to_solve(NTU, Cr, effectiveness):
            return (1. - exp(1./Cr*NTU**0.22*(exp(-Cr*NTU**0.78) - 1.))) - effectiveness
        return ridder(to_solve, a=1E-7, b=1E5, args=(Cr, effectiveness))
    
    elif subtype == 'crossflow, mixed Cmin':
        if Cr*log(1. - effectiveness) < -1:
            raise Exception('The specified effectiveness is not physically \
possible for this configuration; the maximum effectiveness possible is %s.' % (1. - exp(-1./Cr)))
        return -1./Cr*log(Cr*log(1. - effectiveness) + 1.)
    
    elif subtype ==  'crossflow, mixed Cmax':
        if 1./Cr*log(1. - effectiveness*Cr) < -1:
            raise Exception('The specified effectiveness is not physically \
possible for this configuration; the maximum effectiveness possible is %s.' % (((exp(Cr) - 1.0)*exp(-Cr)/Cr)))
        return -log(1. + 1./Cr*log(1. - effectiveness*Cr))
    
    elif subtype in ['boiler', 'condenser']:
        return -log(1. - effectiveness)
    else:
        raise Exception('Input heat exchanger type not recognized')


def calc_Cmin(mh, mc, Cph, Cpc):
    r'''Returns the heat capacity rate for the minimum stream
    having flows `mh` and `mc`, with averaged heat capacities `Cph` and `Cpc`.

    .. math::
        C_c = m_cC_{p,c}

        C_h = m_h C_{p,h}

        C_{min} = \min(C_c, C_h)

    Parameters
    ----------
    mh : float
        Mass flow rate of hot stream, [kg/s]
    mc : float
        Mass flow rate of cold stream, [kg/s]
    Cph : float
        Averaged heat capacity of hot stream, [J/kg/K]
    Cpc : float
        Averaged heat capacity of cold stream, [J/kg/K]

    Returns
    -------
    Cmin : float
        The heat capacity rate of the smaller fluid, [W/K]

    Notes
    -----
    Used with the effectiveness method for heat exchanger design.
    Technically, it doesn't matter if the hot and cold streams are in the right
    order for the input, but it is easiest to use this function when the order
    is specified.

    Examples
    --------
    >>> calc_Cmin(mh=22., mc=5.5, Cph=2200, Cpc=4400.)
    24200.0

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    Ch = mh*Cph
    Cc = mc*Cpc
    return min(Ch, Cc)


def calc_Cmax(mh, mc, Cph, Cpc):
    r'''Returns the heat capacity rate for the maximum stream
    having flows `mh` and `mc`, with averaged heat capacities `Cph` and `Cpc`.

    .. math::
        C_c = m_cC_{p,c}

        C_h = m_h C_{p,h}

        C_{max} = \max(C_c, C_h)

    Parameters
    ----------
    mh : float
        Mass flow rate of hot stream, [kg/s]
    mc : float
        Mass flow rate of cold stream, [kg/s]
    Cph : float
        Averaged heat capacity of hot stream, [J/kg/K]
    Cpc : float
        Averaged heat capacity of cold stream, [J/kg/K]

    Returns
    -------
    Cmax : float
        The heat capacity rate of the larger fluid, [W/K]

    Notes
    -----
    Used with the effectiveness method for heat exchanger design.
    Technically, it doesn't matter if the hot and cold streams are in the right
    order for the input, but it is easiest to use this function when the order
    is specified.

    Examples
    --------
    >>> calc_Cmax(mh=22., mc=5.5, Cph=2200, Cpc=4400.)
    48400.0

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    Ch = mh*Cph
    Cc = mc*Cpc
    return max(Ch, Cc)


def calc_Cr(mh, mc, Cph, Cpc):
    r'''Returns the heat capacity rate ratio for a heat exchanger
    having flows `mh` and `mc`, with averaged heat capacities `Cph` and `Cpc`.

    .. math::
        C_r=C^*=\frac{C_{min}}{C_{max}}

    Parameters
    ----------
    mh : float
        Mass flow rate of hot stream, [kg/s]
    mc : float
        Mass flow rate of cold stream, [kg/s]
    Cph : float
        Averaged heat capacity of hot stream, [J/kg/K]
    Cpc : float
        Averaged heat capacity of cold stream, [J/kg/K]

    Returns
    -------
    Cr : float
        The heat capacity rate ratio, of the smaller fluid to the larger
        fluid, [W/K]

    Notes
    -----
    Used with the effectiveness method for heat exchanger design.
    Technically, it doesn't matter if the hot and cold streams are in the right
    order for the input, but it is easiest to use this function when the order
    is specified.

    Examples
    --------
    >>> calc_Cr(mh=22., mc=5.5, Cph=2200, Cpc=4400.)
    0.5

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    Ch = mh*Cph
    Cc = mc*Cpc
    Cmin = min(Ch, Cc)
    Cmax = max(Ch, Cc)
    return Cmin/Cmax


def NTU_from_UA(UA, Cmin):
    r'''Returns the Number of Transfer Units for a heat exchanger having
    `UA`, and with `Cmin` heat capacity rate.

    .. math::
        NTU = \frac{UA}{C_{min}}

    Parameters
    ----------
    UA : float
        Combined Area-heat transfer coefficient term, [W/K]
    Cmin : float
        The heat capacity rate of the smaller fluid, [W/K]

    Returns
    -------
    NTU : float
        Thermal Number of Transfer Units [-]

    Notes
    -----
    Used with the effectiveness method for heat exchanger design.

    Examples
    --------
    >>> NTU_from_UA(4400., 22.)
    200.0

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    return UA/Cmin


def UA_from_NTU(NTU, Cmin):
    r'''Returns the combined area-heat transfer term for a heat exchanger
    having a specified `NTU`, and with `Cmin` heat capacity rate.

    .. math::
        UA = NTU C_{min}

    Parameters
    ----------
    NTU : float
        Thermal Number of Transfer Units [-]
    Cmin : float
        The heat capacity rate of the smaller fluid, [W/K]

    Returns
    -------
    UA : float
        Combined area-heat transfer coefficient term, [W/K]

    Notes
    -----
    Used with the effectiveness method for heat exchanger design.

    Examples
    --------
    >>> UA_from_NTU(200., 22.)
    4400.0

    References
    ----------
    .. [1] Bergman, Theodore L., Adrienne S. Lavine, Frank P. Incropera, and
       David P. DeWitt. Introduction to Heat Transfer. 6E. Hoboken, NJ:
       Wiley, 2011.
    '''
    return NTU*Cmin


def effectiveness_NTU_method(mh, mc, Cph, Cpc, subtype='counterflow', Thi=None, 
                             Tho=None, Tci=None, Tco=None, UA=None):
    r'''Wrapper for the various effectiveness-NTU method function calls,
    which can solve a heat exchanger. The heat capacities and mass flows
    of each stream and the type of the heat exchanger are always required.
    As additional inputs, one combination of the following inputs is required:
        
    * Three of the four inlet and outlet stream temperatures.
    * Temperatures for the cold outlet and hot outlet and UA
    * Temperatures for the cold inlet and hot inlet and UA
    * Temperatures for the cold inlet and hot outlet and UA
    * Temperatures for the cold outlet and hot inlet and UA
    * Boiler or condenser
      
    Parameters
    ----------
    mh : float
        Mass flow rate of hot stream, [kg/s]
    mc : float
        Mass flow rate of cold stream, [kg/s]
    Cph : float
        Averaged heat capacity of hot stream, [J/kg/K]
    Cpc : float
        Averaged heat capacity of cold stream, [J/kg/K]
    subtype : str, optional
        The subtype of exchanger; one of 'counterflow', 'parallel', 'crossflow'
        'crossflow, mixed Cmin', 'crossflow, mixed Cmax', 'boiler', 'condenser',
        'S&T', or 'nS&T' where n is the number of shell and tube exchangers in 
        a row
    Thi : float, optional
        Inlet temperature of hot fluid, [K]
    Tho : float, optional
        Outlet temperature of hot fluid, [K]
    Tci : float, optional
        Inlet temperature of cold fluid, [K]
    Tco : float, optional
        Outlet temperature of cold fluid, [K]
    UA : float, optional
        Combined Area-heat transfer coefficient term, [W/K]

    Returns
    -------
    results : dict
        * Q : Heat exchanged in the heat exchanger, [W]
        * UA : Combined area-heat transfer coefficient term, [W/K]
        * Cr : The heat capacity rate ratio, of the smaller fluid to the larger
          fluid, [W/K]
        * Cmin : The heat capacity rate of the smaller fluid, [W/K]
        * Cmax : The heat capacity rate of the larger fluid, [W/K]
        * effectiveness : The thermal effectiveness of the heat exchanger, [-]
        * NTU : Thermal Number of Transfer Units [-]
        * Thi : Inlet temperature of hot fluid, [K]
        * Tho : Outlet temperature of hot fluid, [K]
        * Tci : Inlet temperature of cold fluid, [K]
        * Tco : Outlet temperature of cold fluid, [K]
    
    See also
    --------
    effectiveness_from_NTU
    NTU_from_effectiveness

    Examples
    --------
    Solve a heat exchanger to determine UA and effectiveness given the
    configuration, flows, subtype, the cold inlet/outlet temperatures, and the
    hot stream inlet temperature.
    
    >>> pprint(effectiveness_NTU_method(mh=5.2, mc=1.45, Cph=1860., Cpc=1900, 
    ... subtype='crossflow, mixed Cmax', Tci=15, Tco=85, Thi=130))
    {'Cmax': 9672.0,
     'Cmin': 2755.0,
     'Cr': 0.2848428453267163,
     'NTU': 1.1040839095588,
     'Q': 192850.0,
     'Tci': 15,
     'Tco': 85,
     'Thi': 130,
     'Tho': 110.06100082712986,
     'UA': 3041.751170834494,
     'effectiveness': 0.6086956521739131}
    
    Solve the same heat exchanger with the UA specified, and known inlet
    temperatures:
        
    >>> pprint(effectiveness_NTU_method(mh=5.2, mc=1.45, Cph=1860., Cpc=1900, 
    ... subtype='crossflow, mixed Cmax', Tci=15, Thi=130, UA=3041.75))
    {'Cmax': 9672.0,
     'Cmin': 2755.0,
     'Cr': 0.2848428453267163,
     'NTU': 1.1040834845735028,
     'Q': 192849.96310220254,
     'Tci': 15,
     'Tco': 84.99998660697007,
     'Thi': 130,
     'Tho': 110.06100464203861,
     'UA': 3041.75,
     'effectiveness': 0.6086955357127832}
    '''
    Cmin = calc_Cmin(mh=mh, mc=mc, Cph=Cph, Cpc=Cpc)
    Cmax = calc_Cmax(mh=mh, mc=mc, Cph=Cph, Cpc=Cpc)
    Cr = calc_Cr(mh=mh, mc=mc, Cph=Cph, Cpc=Cpc)
    Cc = mc*Cpc
    Ch = mh*Cph
    if UA is not None:
        NTU = NTU_from_UA(UA=UA, Cmin=Cmin)
        effectiveness = eff = effectiveness_from_NTU(NTU=NTU, Cr=Cr, subtype=subtype)
        
        possible_inputs = [(Tci, Thi), (Tci, Tho), (Tco, Thi), (Tco, Tho)]
        if not any([i for i in possible_inputs if None not in i]):
            raise Exception('One set of (Tci, Thi), (Tci, Tho), (Tco, Thi), or (Tco, Tho) are required along with UA.')
        
        if Thi and Tci:
            Q = eff*Cmin*(Thi - Tci)
        elif Tho and Tco :
            Q = eff*Cmin*Cc*Ch*(Tco - Tho)/(eff*Cmin*(Cc+Ch) - Ch*Cc)
        elif Thi and Tco:
            Q = Cmin*Cc*eff*(Tco-Thi)/(eff*Cmin - Cc)
        elif Tho and Tci:
            Q = Cmin*Ch*eff*(Tci-Tho)/(eff*Cmin - Ch)
        # The following is not used as it was decided to require complete temperature information
#        elif Tci and Tco:
#            Q = Cc*(Tco - Tci)
#        elif Tho and Thi:
#            Q = Ch*(Thi-Tho)
        # Compute the remaining temperatures with the fewest lines of code
        if Tci and not Tco:
            Tco = Tci + Q/(Cc)
        else:
            Tci = Tco - Q/(Cc)
        if Thi and not Tho:
            Tho = Thi - Q/(Ch)
        else:
            Thi = Tho + Q/(Ch)        
    
    elif UA is None:
        # Case where we're solving for UA
        # Three temperatures are required
        # Ensures all four temperatures are set and Q is calculated
        if Thi is not None and Tho is not None:
            Q = mh*Cph*(Thi-Tho)
            if Tci is not None and Tco is None:
                Tco = Tci + Q/(mc*Cpc)
            elif Tco is not None and Tci is None:
                Tci = Tco - Q/(mc*Cpc)
            elif Tco is not None and Tci is not None:
                Q2 = mc*Cpc*(Tco-Tci)
                if abs((Q-Q2)/Q) > 0.01:
                    raise Exception('The specified heat capacities, mass flows, and temperatures are inconsistent')
            else:
                raise Exception('At least one temperature is required to be specified on the cold side.')
                
        elif Tci is not None and Tco is not None:
            Q = mc*Cpc*(Tco-Tci)
            if Thi is not None and Tho is None:
                Tho = Thi - Q/(mh*Cph)
            elif Tho is not None and Thi is None:
                Thi = Tho + Q/(mh*Cph)
            else:
                raise Exception('At least one temperature is required to be specified on the cold side.')

        effectiveness = Q/Cmin/(Thi-Tci)
        NTU = NTU_from_effectiveness(effectiveness, Cr, subtype=subtype)
        UA = UA_from_NTU(NTU, Cmin)    
    return {'Q': Q, 'UA': UA, 'Cr':Cr, 'Cmin': Cmin, 'Cmax':Cmax, 
            'effectiveness': effectiveness, 'NTU': NTU, 'Thi': Thi, 'Tho': Tho,
            'Tci': Tci, 'Tco': Tco} 


def temperature_effectiveness_basic(R1, NTU1, subtype='crossflow'):
    r'''Returns temperature effectiveness `P1` of a heat exchanger with 
    a specified heat capacity ratio, number of transfer units `NTU1`,
    and of type `subtype`. This function performs the calculations for the
    basic cases, not actual shell-and-tube exchangers. The suported cases
    are as follows:
        
    * Counterflow (ex. double-pipe)
    * Parallel (ex. double pipe inefficient configuration)
    * Crossflow, single pass, fluids unmixed
    * Crossflow, single pass, fluid 1 mixed, fluid 2 unmixed
    * Crossflow, single pass, fluid 2 mixed, fluid 1 unmixed
    * Crossflow, single pass, both fluids mixed
    
    For parallel flow heat exchangers (this configuration is symmetric):

    .. math::
        P_1 = \frac{1 - \exp[-NTU_1(1+R_1)]}{1 + R_1}

    For counterflow heat exchangers (this configuration is symmetric):

    .. math::
        P_1 = \frac{1 - \exp[-NTU_1(1-R_1)]}{1 - R_1 \exp[-NTU_1(1-R_1)]}

    For cross-flow (single-pass) heat exchangers with both fluids unmixed
    (this configuration is symmetric):

    .. math::
        P_1 \approx 1 - \exp\left[\frac{NTU_1^{0.22}}{R_1}
        (\exp(-R_1 NTU_1^{0.78})-1)\right]

    For cross-flow (single-pass) heat exchangers with fluid 1 mixed, fluid 2
    unmixed:

    .. math::
        P_1 = 1 - \exp\left(-\frac{K}{R_1}\right)
        
        K = 1 - \exp(-R_1 NTU_1)

    For cross-flow (single-pass) heat exchangers with fluid 2 mixed, fluid 1 
    unmixed:

    .. math::
        P_1 = \frac{1 - \exp(-K R_1)}{R_1}
        
        K = 1 - \exp(-NTU_1)

    For cross-flow (single-pass) heat exchangers with both fluids mixed 
    (this configuration is symmetric):

    .. math::
        P_1 = \left(\frac{1}{K_1} + \frac{R_1}{K_2} - \frac{1}{NTU_1}\right)^{-1}
        
        K_1 = 1 - \exp(-NTU_1)
        
        K_2 = 1 - \exp(-R_1 NTU_1)
        
    Parameters
    ----------
    R1 : float
        Heat capacity ratio of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]
    NTU1 : float
        Thermal number of transfer units of the heat exchanger in the P-NTU 
        method, calculated with respect to stream 1 [-]
    subtype : float
        The type of heat exchanger; one of 'counterflow', 'parallel', 
        'crossflow', 'crossflow, mixed 1', 'crossflow, mixed 2', 
        'crossflow, mixed 1&2'.
        
    Returns
    -------
    P1 : float
        Thermal effectiveness of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]

    Notes
    -----
    The crossflow case is an approximation only. There is an actual
    solution involving an infinite sum. This was implemented, but found to 
    differ substantially so the approximation is used instead.

    Examples
    --------
    >>> temperature_effectiveness_basic(R1=.1, NTU1=4, subtype='counterflow')
    0.9753412729761263

    References
    ----------
    .. [1] Shah, Ramesh K., and Dusan P. Sekulic. Fundamentals of Heat 
       Exchanger Design. 1st edition. Hoboken, NJ: Wiley, 2002.
    .. [2] Thulukkanam, Kuppan. Heat Exchanger Design Handbook, Second Edition. 
       CRC Press, 2013.
    .. [3] Rohsenow, Warren and James Hartnett and Young Cho. Handbook of Heat
       Transfer, 3E. New York: McGraw-Hill, 1998.
    '''
    if subtype == 'counterflow':
        P1 = (1 - exp(-NTU1*(1 - R1)))/(1 - R1*exp(-NTU1*(1-R1)))
    elif subtype == 'parallel':
        P1 = (1 - exp(-NTU1*(1 + R1)))/(1 + R1)
    elif subtype == 'crossflow':
        # This isn't technically accurate, an infinite sum is required
        # It has been computed from two different sources
        # but is found not to be within the 1% claimed of this equation
        P1 = 1 - exp(NTU1**0.22/R1*(exp(-R1*NTU1**0.78) - 1.))
    elif subtype == 'crossflow, mixed 1':
        # Not symmetric
        K = 1 - exp(-R1*NTU1)
        P1 = 1 - exp(-K/R1)
    elif subtype == 'crossflow, mixed 2':
        # Not symmetric
        K = 1 - exp(-NTU1)
        P1 = (1 - exp(-K*R1))/R1
    elif subtype == 'crossflow, mixed 1&2':
        K1 = 1 - exp(-NTU1)
        K2 = 1 - exp(-R1*NTU1)
        P1 = (1./K1 + R1/K2 - 1./NTU1)**-1
    else:
        raise Exception('Subtype not recognized.')
    return P1


def temperature_effectiveness_TEMA_J(R1, NTU1, Ntp):
    r'''Returns temperature effectiveness `P1` of a TEMA J type heat exchanger  
    with a specified heat capacity ratio, number of transfer units `NTU1`,
    and of number of tube passes `Ntp`. The suported cases are as follows:
        
    * One tube pass (shell fluid mixed)
    * Two tube passes (shell fluid mixed, tube pass mixed between passes)
    * Four tube passes (shell fluid mixed, tube pass mixed between passes)
    
    For 1-1 TEMA J shell and tube exchangers, shell and tube fluids mixed:

    .. math::
        P_1 = \frac{1}{R_1}\left[1- \frac{(2-R_1)(2E + R_1 B)}{(2+R_1)
        (2E - R_1/B)}\right]
        
    For 1-2 TEMA J, shell and tube fluids mixed. There are two possible 
    arrangements for the flow and the number of tube passes, but the equation
    is the same in both:
        
    .. math::
        P_1 = \left[1 + \frac{R_1}{2} + \lambda B - 2\lambda C D\right]^{-1}
        
        B = \frac{(A^\lambda +1)}{A^\lambda -1}
        
        C = \frac{A^{(1 + \lambda)/2}}{\lambda - 1 + (1 + \lambda)A^\lambda}
        
        D = 1 + \frac{\lambda A^{(\lambda-1)/2}}{A^\lambda -1}
        
        A = \exp(NTU_1)
        
        \lambda = (1 + R_1^2/4)^{0.5}
        
    For 1-4 TEMA J, shell and tube exchanger with both sides mixed:
        
    .. math::
        P_1 = \left[1 + \frac{R_1}{4}\left(\frac{1+3E}{1+E}\right) + \lambda B 
        - 2 \lambda C D\right]^{-1}
        
        B = \frac{A^\lambda +1}{A^\lambda -1}
        
        C = \frac{A^{(1+\lambda)/2}}{\lambda - 1 + (1 + \lambda)A^\lambda}
        
        D = 1 + \frac{\lambda A^{(\lambda-1)/2}}{A^\lambda -1}
        
        A = \exp(NTU_1)
        
        E = \exp(R_1 NTU_1/2)
        
        \lambda = (1 + R_1^2/16)^{0.5}
        
    Parameters
    ----------
    R1 : float
        Heat capacity ratio of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]
    NTU1 : float
        Thermal number of transfer units of the heat exchanger in the P-NTU 
        method, calculated with respect to stream 1 [-]
    Ntp : int
        Number of tube passes, 1, 2, or 4, [-]
        
    Returns
    -------
    P1 : float
        Thermal effectiveness of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]

    Notes
    -----
    For numbers of tube passes greater than 4 or 3, an exception is raised.

    Examples
    --------
    >>> temperature_effectiveness_TEMA_J(R1=1/3., NTU1=1., Ntp=1)
    0.5699085193651295

    References
    ----------
    .. [1] Shah, Ramesh K., and Dusan P. Sekulic. Fundamentals of Heat 
       Exchanger Design. 1st edition. Hoboken, NJ: Wiley, 2002.
    .. [2] Thulukkanam, Kuppan. Heat Exchanger Design Handbook, Second Edition. 
       CRC Press, 2013.
    .. [3] Rohsenow, Warren and James Hartnett and Young Cho. Handbook of Heat
       Transfer, 3E. New York: McGraw-Hill, 1998.
    '''
    if Ntp == 1:
        A = exp(NTU1)
        B = exp(-NTU1*R1/2.)
        if R1 != 2:
            P1 = 1./R1*(1. - (2. - R1)*(2.*A + R1*B)/(2. + R1)/(2.*A - R1/B))
        else:
            P1 = 0.5*(1. - (1. + A**-2)/2./(1. + NTU1))
    elif Ntp == 2:
        lambda1 = (1. + R1**2/4.)**0.5
        A = exp(NTU1)
        D = 1. + lambda1*A**((lambda1 - 1.)/2.)/(A**lambda1 - 1.)
        C = A**((1+lambda1)/2.)/(lambda1 - 1. + (1. + lambda1)*A**lambda1)
        B = (A**lambda1 + 1.)/(A**lambda1 - 1.)
        P1 = 1./(1. + R1/2. + lambda1*B - 2.*lambda1*C*D)
    elif Ntp == 4:
        lambda1 = (1. + R1**2/16.)**0.5
        E = exp(R1*NTU1/2.)
        A = exp(NTU1)
        D = 1. + lambda1*A**((lambda1-1)/2.)/(A**lambda1-1.)
        C = A**((1+lambda1)/2.)/(lambda1 - 1. + (1. + lambda1)*A**lambda1)
        B = (A**lambda1 + 1.)/(A**lambda1-1)
        P1 = 1./(1. + R1/4.*(1. + 3.*E)/(1. + E) + lambda1*B - 2.*lambda1*C*D)
    else:
        raise Exception('Supported numbers of tube passes are 1, 2, and 4.')
    return P1


def temperature_effectiveness_TEMA_H(R1, NTU1, Ntp, optimal=True):
    r'''Returns temperature effectiveness `P1` of a TEMA H type heat exchanger  
    with a specified heat capacity ratio, number of transfer units `NTU1`,
    and of number of tube passes `Ntp`. For the two tube pass case, there are
    two possible orientations, one inefficient and one efficient controlled
    by the `optimal` option. The suported cases are as follows:
        
    * One tube pass (tube fluid split into two streams individually mixed,  
      shell fluid mixed)
    * Two tube passes (shell fluid mixed, tube pass mixed between passes)
    * Two tube passes (shell fluid mixed, tube pass mixed between passes, inlet
      tube side next to inlet shell-side)
    
    1-1 TEMA H, tube fluid split into two streams individually mixed, shell 
    fluid mixed:

    .. math::
        P_1 = E[1 + (1 - BR_1/2)(1 - A R_1/2 + ABR_1)] - AB(1 - BR_1/2)
        
        A = \frac{1}{1 + R_1/2}\{1 - \exp[-NTU_1(1 + R_1/2)/2]\}
        
        B = \frac{1-D}{1-R_1 D/2}
        
        D = \exp[-NTU_1(1-R_1/2)/2]
        
        E = (A + B - ABR_1/2)/2
        
    1-2 TEMA H, shell and tube fluids mixed in each pass at the cross section:
        
    .. math::
        P_1 = \frac{1}{R_1}\left[1 - \frac{(1-D)^4}{B - 4G/R_1}\right]
        
        B = (1+H)(1+E)^2
        
        G = (1-D)^2(D^2 + E^2) + D^2(1 + E)^2
        
        H = [1 - \exp(-2\beta)]/(4/R_1 -1)
        
        E = [1 - \exp(-\beta)]/(4/R_1 - 1)
        
        D = [1 - \exp(-\alpha)]/(4/R_1 + 1)
        
        \alpha = NTU_1(4 + R_1)/8
        
        \beta = NTU_1(4-R_1)/8
        
    1-2 TEMA H, shell and tube fluids mixed in each pass at the cross section
    but with the inlet tube stream coming in next to the shell fluid inlet
    in an inefficient way (this is only shown in [2]_, and the stream 1/2 
    convention in it is different but converted here; P1 is still returned):
        
    .. math::
        P_2 = \left[1 - \frac{B + 4GR_2}{(1-D)^4}\right]
    
        B = (1 + H)(1 + E)^2
        
        G = (1-D)^2(D^2 + E^2) + D^2(1 + E)^2
        
        D = \frac{1 - \exp(-\alpha)}{1 - 4R_2}
        
        E = \frac{\exp(-\beta) - 1}{4R_2 +1}
        
        H = \frac{\exp(-2\beta) - 1}{4R_2 +1}
        
        \alpha = \frac{NTU_2}{8}(4R_2 -1)
        
        \beta = \frac{NTU_2}{8}(4R_2 +1)
                
    Parameters
    ----------
    R1 : float
        Heat capacity ratio of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]
    NTU1 : float
        Thermal number of transfer units of the heat exchanger in the P-NTU 
        method, calculated with respect to stream 1 [-]
    Ntp : int
        Number of tube passes, 1, or 2, [-]
        
    Returns
    -------
    P1 : float
        Thermal effectiveness of the heat exchanger in the P-NTU method,
        calculated with respect to stream 1 [-]

    Notes
    -----
    For numbers of tube passes greater than 1 or 2, an exception is raised.

    Examples
    --------
    >>> temperature_effectiveness_TEMA_H(R1=1/3., NTU1=1., Ntp=1)
    0.5730728284905833

    References
    ----------
    .. [1] Shah, Ramesh K., and Dusan P. Sekulic. Fundamentals of Heat 
       Exchanger Design. 1st edition. Hoboken, NJ: Wiley, 2002.
    .. [2] Thulukkanam, Kuppan. Heat Exchanger Design Handbook, Second Edition. 
       CRC Press, 2013.
    .. [3] Rohsenow, Warren and James Hartnett and Young Cho. Handbook of Heat
       Transfer, 3E. New York: McGraw-Hill, 1998.
    '''
    if Ntp == 1:
        A = 1./(1 + R1/2.)*(1. - exp(-NTU1*(1. + R1/2.)/2.))
        D = exp(-NTU1*(1. - R1/2.)/2.)
        if R1 != 2:
            B = (1. - D)/(1. - R1*D/2.)
        else:
            B = NTU1/(2. + NTU1)
        E = (A + B - A*B*R1/2.)/2.
        P1 = E*(1. + (1. - B*R1/2.)*(1. - A*R1/2. + A*B*R1)) - A*B*(1. - B*R1/2.)
    elif Ntp == 2 and optimal:
        alpha = NTU1*(4. + R1)/8.
        beta = NTU1*(4. - R1)/8.
        D = (1. - exp(-alpha))/(4./R1 + 1)
        if R1 != 4:
            E = (1. - exp(-beta))/(4./R1 - 1.)
            H = (1. - exp(-2.*beta))/(4./R1 - 1.)
        else:
            E = NTU1/2.
            H = NTU1
        G = (1-D)**2*(D**2 + E**2) + D**2*(1+E)**2
        B = (1. + H)*(1. + E)**2
        P1 = 1./R1*(1. - (1. - D)**4/(B - 4.*G/R1))
    elif Ntp == 2 and not optimal:
        R1_orig = R1
        #NTU2 = NTU1*R1_orig but we want to treat it as NTU1 in this case
        NTU1 = NTU1*R1_orig # switch 1
        # R2 = 1/R1 but we want to treat it as R1 in this case
        R1 = 1./R1_orig # switch 2
        
        beta = NTU1*(4.*R1 + 1)/8.
        alpha = NTU1/8.*(4.*R1 - 1.)
        H = (exp(-2.*beta) - 1.)/(4.*R1 + 1.)
        E = (exp(-beta) - 1.)/(4.*R1 + 1.)
        B = (1. + H)*(1. + E)**2
        if R1 != 0.25:
            D = (1. - exp(-alpha))/(1. - 4.*R1)
            G = (1. - D)**2*(D**2 + E**2) + D**2*(1. + E)**2
            P1 = (1. - (B + 4.*G*R1)/(1. - D)**4)
        else:
            D = -NTU1/8.
            G = (1. - D)**2*(D**2 + E**2) + D**2*(1. + E)**2
            P1 = (1. - (B + 4.*G*R1)/(1. - D)**4)
        P1 = P1/R1_orig # switch 3, confirmed
    else:
        raise Exception('Number of tube passes exceeds available correlation data')
    return P1


def F_LMTD_Fakheri(Thi, Tho, Tci, Tco, shells=1):
    r'''Calculates the log-mean temperature difference correction factor `Ft` 
    for a shell-and-tube heat exchanger with one or an even number of tube 
    passes, and a given number of shell passes, with the expression given in 
    [1]_ and also shown in [2]_.
    
    .. math::
        F_t=\frac{S\ln W}{\ln \frac{1+W-S+SW}{1+W+S-SW}}

        S = \frac{\sqrt{R^2+1}}{R-1}
        
        W = \left(\frac{1-PR}{1-P}\right)^{1/N}
        
        R = \frac{T_{in}-T_{out}}{t_{out}-t_{in}}
        
        P = \frac{t_{out}-t_{in}}{T_{in}-t_{in}}
        
    If R = 1 and logarithms cannot be evaluated:
        
    .. math::
        W' = \frac{N-NP}{N-NP+P}
        
        F_t = \frac{\sqrt{2}\frac{1-W'}{W'}}{\ln\frac{\frac{W'}{1-W'}+\frac{1}
        {\sqrt{2}}}{\frac{W'}{1-W'}-\frac{1}{\sqrt{2}}}}
        
    Parameters
    ----------
    Thi : float
        Inlet temperature of hot fluid, [K]
    Tho : float
        Outlet temperature of hot fluid, [K]
    Tci : float
        Inlet temperature of cold fluid, [K]
    Tco : float
        Outlet temperature of cold fluid, [K]        
    shells : int, optional
        Number of shell-side passes, [-]

    Returns
    -------
    Ft : float
        Log-mean temperature difference correction factor, [-]

    Notes
    -----
    This expression is symmetric - the same result is calculated if the cold
    side values are swapped with the hot side values. It also does not 
    depend on the units of the temperature given.

    Examples
    --------
    >>> F_LMTD_Fakheri(Tci=15, Tco=85, Thi=130, Tho=110, shells=1)
    0.9438358829645933

    References
    ----------
    .. [1] Fakheri, Ahmad. "A General Expression for the Determination of the 
       Log Mean Temperature Correction Factor for Shell and Tube Heat 
       Exchangers." Journal of Heat Transfer 125, no. 3 (May 20, 2003): 527-30.
       doi:10.1115/1.1571078.
    .. [2] Hall, Stephen. Rules of Thumb for Chemical Engineers, Fifth Edition.
       Oxford; Waltham, MA: Butterworth-Heinemann, 2012.
    '''
    R = (Thi - Tho)/(Tco - Tci)
    P = (Tco - Tci)/(Thi - Tci)
    if R == 1.0:
        W2 = (shells - shells*P)/(shells - shells*P + P)
        return (2**0.5*(1. - W2)/W2)/log(((W2/(1. - W2) + 2**-0.5)/(W2/(1. - W2) - 2**-0.5)))
    else:
        W = ((1. - P*R)/(1. - P))**(1./shells)
        S = (R*R + 1.)**0.5/(R - 1.)
        return S*log(W)/log((1. + W - S + S*W)/(1. + W + S - S*W))

### Tubes

# TEMA tubes from http://www.engineeringpage.com/technology/thermal/tubesize.html
# NPSs in inches, which convert to outer diameter exactly.
_NPSs = [0.25, 0.25, 0.375, 0.375, 0.375, 0.5, 0.5, 0.625, 0.625, 0.625, 0.75, 0.75, 0.75, 0.75, 0.75, 0.875, 0.875, 0.875, 0.875, 1, 1, 1, 1, 1.25, 1.25, 1.25, 1.25, 2, 2]
_Dos = [ i/1000. for i in [6.35, 6.35, 9.525, 9.525, 9.525, 12.7, 12.7, 15.875, 15.875, 15.875, 19.05, 19.05, 19.05, 19.05, 19.05, 22.225, 22.225, 22.225, 22.225, 25.4, 25.4, 25.4, 25.4, 31.75, 31.75, 31.75, 31.75, 50.8, 50.8]]
_BWGs = [22, 24, 18, 20, 22, 18, 20, 16, 18, 20, 12, 14, 16, 18, 20, 14, 16, 18, 20, 12, 14, 16, 18, 10, 12, 14, 16, 12, 14]
_ts = [i/1000. for i in [0.711, 0.559, 1.245, 0.889, 0.711, 1.245, 0.889, 1.651, 1.245, 0.889, 2.769, 2.108, 1.651, 1.245, 0.889, 2.108, 1.651, 1.245, 0.889, 2.769, 2.108, 1.651, 1.245, 3.404, 2.769, 2.108, 1.651, 2.769, 2.108]]
_Dis = [i/1000. for i in [4.928, 5.232, 7.035, 7.747, 8.103, 10.21, 10.922, 12.573, 13.385, 14.097, 13.512, 14.834, 15.748, 16.56, 17.272, 18.009, 18.923, 19.735, 20.447, 19.862, 21.184, 22.098, 22.91, 24.942, 26.212, 27.534, 28.448, 45.262, 46.584]]

# Structure: Look up NPS, get BWGs. BWGs listed in increasing order --> decreasing thickness
TEMA_tubing = {0.25: (22, 24), 0.375: (18, 20, 22), 0.5: (18, 20),
0.625: (16, 18, 20), 0.75: (12, 14, 16, 18, 20),
0.875: (14, 16, 18, 20), 1.: (12, 14, 16, 18),
1.25: (10, 12, 14, 16), 2.: (12, 14)}

#TEMA_Full_Tubing = [(6.35,22), (6.35,24), (6.35,26), (6.35,27), (9.53,18), (9.53,20), (9.53,22), (9.53,24), (12.7,16), (12.7,16), (12.7,20), (12.7,22), (15.88,12), (15.88,13), (15.88,14), (15.88,15), (15.88,16), (15.88,17), (15.88,18), (15.88,19), (15.88,20), (19.05,10), (19.05,11), (19.05,12), (19.05,13), (19.05,14), (19.05,15), (19.05,16), (19.05,17), (19.05,18), (19.05,20), (22.23,10), (22.23,11), (22.23,12), (22.23,13), (22.23,14), (22.23,15), (22.23,16), (22.23,17), (22.23,18), (22.23,20), (25.4,8), (25.4,10), (25.4,11), (25.4,12), (25.4,13), (25.4,14), (25.4,15), (25.4,16), (25.4,18), (25.4,20), (31.75,7), (31.75,8), (31.75,10), (31.75,11), (31.75,12), (31.75,13), (31.75,14), (31.75,16), (31.75,18), (31.75,20), (38.1,10), (38.1,12), (38.1,14), (38.1,16), (50.8,11), (50.8,12), (50.8,13), (50.8,14), (63.5,10), (63.5,12), (63.5,14), (76.2,10), (76.2,12), (76.2,14)]
#BWG_integers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
#BWG_inch = [0.34, 0.3, 0.284, 0.259, 0.238, 0.22, 0.203, 0.18, 0.165, 0.148, 0.134, 0.12, 0.109, 0.095, 0.083, 0.072, 0.065, 0.058, 0.049, 0.042, 0.035, 0.032, 0.028, 0.025, 0.022, 0.02, 0.018, 0.016, 0.014, 0.013, 0.012, 0.01, 0.009, 0.008, 0.007, 0.005, 0.004]
#BWG_SI = [round(i*.0254,6) for i in BWG_inch]
#
#for tup in TEMA_Full_Tubing:
#    Do, BWG = tup[0]/1000., tup[1]
#    t = BWG_SI[BWG_integers.index(BWG)]
#    Di = Do-2*t
#    print t*1000, Di*1000
#
def check_tubing_TEMA(NPS=None, BWG=None):
    '''
    >>> check_tubing_TEMA(2, 22)
    False
    >>> check_tubing_TEMA(0.375, 22)
    True
    '''
    if NPS in TEMA_tubing:
        if BWG in TEMA_tubing[NPS]:
            return True
    return False


def get_tube_TEMA(NPS=None, BWG=None, Do=None, Di=None, tmin=None):
    # Tube defined by a thickness and an outer diameter only, no pipe.
    # If Di or Do are specified, they must be exactly correct.
    if NPS and BWG:
        # Fully defined, guaranteed
        if not check_tubing_TEMA(NPS, BWG):
            raise Exception('NPS and BWG Specified are not listed in TEMA')
        Do = 0.0254*NPS
        t = BWG_SI[BWG_integers.index(BWG)]
        Di = Do-2*t
    elif Do and BWG:
        NPS = Do/.0254
        if not check_tubing_TEMA(NPS, BWG):
            raise Exception('NPS and BWG Specified are not listed in TEMA')
        t = BWG_SI[BWG_integers.index(BWG)]
        Di = Do-2*t
    elif BWG and Di:
        t = BWG_SI[BWG_integers.index(BWG)] # Will fail if BWG not int
        Do = t*2 + Di
        NPS = Do/.0254
        if not check_tubing_TEMA(NPS, BWG):
            raise Exception('NPS and BWG Specified are not listed in TEMA')
    elif NPS and Di:
        Do = 0.0254*NPS
        t = (Do - Di)/2
        BWG = [BWG_integers[BWG_SI.index(t)]]
        if not check_tubing_TEMA(NPS, BWG):
            raise Exception('NPS and BWG Specified are not listed in TEMA')
    elif Di and Do:
        NPS = Do/.0254
        t = (Do - Di)/2
        BWG = [BWG_integers[BWG_SI.index(t)]]
        if not check_tubing_TEMA(NPS, BWG):
            raise Exception('NPS and BWG Specified are not listed in TEMA')
    # Begin Fuzzy matching
    elif NPS and tmin:
        Do = 0.0254*NPS
        ts = [BWG_SI[BWG_integers.index(BWG)] for BWG in TEMA_tubing[NPS]]
        ts.reverse() # Small to large
        if tmin > ts[-1]:
            raise Exception('Specified minimum thickness is larger than available in TEMA')
        for t in ts: # Runs if at least 1 of the thicknesses are the right size.
            if tmin <= t:
                break
        BWG = [BWG_integers[BWG_SI.index(t)]]
        Di = Do-2*t
    elif Do and tmin:
        NPS = Do/.0254
        NPS, BWG, Do, Di, t = get_tube_TEMA(NPS=NPS, tmin=tmin)
    elif Di and tmin:
        raise Exception('Not funny defined input for TEMA Schedule; multiple solutions')
    elif NPS:
        BWG = TEMA_tubing[NPS][0] # Pick the first listed size
        Do = 0.0254*NPS
        t = BWG_SI[BWG_integers.index(BWG)]
        Di = Do-2*t
    else:
        raise Exception('Insufficient information provided')
    return NPS, BWG, Do, Di, t

TEMA_Ls_imperial = [96., 120., 144., 192., 240.] # inches
TEMA_Ls = [2.438, 3.048, 3.658, 4.877, 6.096]
HTRI_Ls_imperial = [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60] # ft
HTRI_Ls = [round(i*0.3048, 3) for i in HTRI_Ls_imperial]


# Shells up to 120 inch in diameter.
# This is for plate shells, not pipe (up to 12 inches, pipe is used)
HEDH_shells_imperial = [12., 13., 14., 15., 16., 17., 18., 19., 20., 21., 22., 24., 26., 28., 30., 32., 34., 36., 38., 40., 42., 44., 46., 48., 50., 52., 54., 56., 58., 60., 63., 66., 69., 72., 75., 78., 81., 84., 87., 90., 93., 96., 99., 102., 105., 108., 111., 114., 117., 120.]
HEDH_shells = [round(i*0.0254, 6) for i in HEDH_shells_imperial]


HEDH_pitches = {0.25: (1.25, 1.5), 0.375: (1.330, 1.420),
0.5: (1.250, 1.310, 1.380), 0.625: (1.250, 1.300, 1.400),
0.75: (1.250, 1.330, 1.420, 1.500), 1.: (1.250, 1.312, 1.375),
1.25: (1.250), 1.5: (1.250), 2.: (1.250)}

def DBundle_min(Do):
    r'''Very roughly, determines a good choice of shell diameter for a given
    tube outer diameter, according to figure 1, section 3.3.5 in [1]_.

    Inputs
    ------
    Do : float
        Tube outer diameter, [m]

    Returns
    -------
    DShell : float
        Shell inner diameter, optional, [m]

    Notes
    -----
    This function should be used if a tube diameter is specified but not a
    shell size. DShell will have to be adjusted later, once the ara requirement
    is known.

    This function is essentially a lookup table.

    Examples
    --------
    >>> DBundle_min(0.0254)
    1.0

    References
    ----------
    .. [1] Schlunder, Ernst U, and International Center for Heat and Mass
       Transfer. Heat Exchanger Design Handbook. Washington:
       Hemisphere Pub. Corp., 1983.
    '''
    if Do <= 0.006:
        DBundle = 0.1
    elif Do <= 0.01:
        DBundle = 0.1
    elif Do <= 0.014:
        DBundle = 0.3
    elif Do <= 0.02:
        DBundle = 0.5
    elif Do <= 0.03:
        DBundle = 1.
    else:
        DBundle = 1.5
    return DBundle


def shell_clearance(DBundle=None, DShell=None):
    r'''Determines the clearance between a shell and tube bundle in a TEMA HX
    [1].

    Inputs
    ------
        DShell : float
            Shell inner diameter, optional, [m]
        DBundle : float
            Outer diameter of tube bundle, optional, [m]

    Returns
    -------
        c : float
            Shell-tube bundle clearance, [m]

    Notes
    -----
    Lower limits are extended up to the next limit where intermediate limits
    are not provided. Only one of shell diameter or bundle are required.

    Examples
    --------
    >>> shell_clearance(DBundle=1.245)
    0.0064

    References
    ----------
    .. [1] Standards of the Tubular Exchanger Manufacturers Association,
       Ninth edition, 2007, TEMA, New York.
    '''
    if DShell:
        if DShell< 0.457:
            c = 0.0032
        elif DShell < 1.016:
            c = 0.0048
        elif DShell < 1.397:
            c = 0.0064
        elif DShell < 1.778:
            c = 0.0079
        elif DShell < 2.159:
            c = 0.0095
        else:
            c = 0.011

    elif DBundle:
        if DBundle < 0.457 - 0.0048:
            c = 0.0032
        elif DBundle < 1.016 - 0.0064:
            c = 0.0048
        elif DBundle < 1.397 - 0.0079:
            c = 0.0064
        elif DBundle < 1.778 - 0.0095:
            c = 0.0079
        elif DBundle <2.159 - 0.011:
            c = 0.0095
        else:
            c = 0.011
    else:
        raise Exception('DShell or DBundle must be specified')
    return c


_TEMA_baffles_refinery = [[0.0032, 0.0048, 0.0064, 0.0095, 0.0095],
[0.0048, 0.0064, 0.0095, 0.0095, 0.0127],
[0.0064, 0.0075, 0.0095, 0.0127, 0.0159],
[0.0064, 0.0095, 0.0127, 0.0159, 0.0159],
[0.0095, 0.0127, 0.0159, 0.0191, 0.0191]]

_TEMA_baffles_other = [[0.0016, 0.0032, 0.0048, 0.0064, 0.0095, 0.0095],
[0.0032, 0.0048, 0.0064, 0.0095, 0.0095, 0.0127],
[0.0048, 0.0064, 0.0075, 0.0095, 0.0127, 0.0159],
[0.0064, 0.0064, 0.0095, 0.0127, 0.0159, 0.0159],
[0.0064, 0.0095, 0.0127, 0.0127, 0.0191, 0.0191]]

def baffle_thickness(Dshell=None, L_unsupported=None, service='C'):
    r'''Determines the thickness of baffles and support plates in TEMA HX
    [1]_. Does not apply to longitudinal baffles.

    Parameters
    ----------
    Dshell : float
        Shell inner diameter, [m]
    L_unsupported: float
        Distance between tube supports, [m]
    service: str
        Service type, C, R or B, [-]

    Returns
    -------
    t : float
        Baffle or support plate thickness, [m]

    Notes
    -----
    No checks are provided to ensure sizes are TEMA compatible.
    As pressure concerns are not relevant, these are simple.
    Mandatory sizes. Uses specified limits in mm.

    Examples
    --------
    >>> baffle_thickness(Dshell=.3, L_unsupported=50, service='R')
    0.0095

    References
    ----------
    .. [1] Standards of the Tubular Exchanger Manufacturers Association,
       Ninth edition, 2007, TEMA, New York.
    '''
    if Dshell < 0.381:
        j = 0
    elif 0.381 <= Dshell < 0.737:
        j = 1
    elif 0.737 <= Dshell < 0.991:
        j = 2
    elif 0.991 <= Dshell  < 1.524:
        j = 3
    else:
        j = 4

    if service == 'R':
        if L_unsupported <= 0.61:
            i = 0
        elif 0.61 < L_unsupported <= 0.914:
            i = 1
        elif 0.914 < L_unsupported <= 1.219:
            i = 2
        elif 1.219 < L_unsupported <= 1.524:
            i = 3
        else:
            i = 4
        t = _TEMA_baffles_refinery[j][i]

    elif service == 'C' or service == 'B':
        if L_unsupported <= 0.305:
            i = 0
        elif 0.305 < L_unsupported <= 0.610:
            i = 1
        elif 0.61 < L_unsupported <= 0.914:
            i = 2
        elif 0.914 < L_unsupported <= 1.219:
            i = 3
        elif 1.219 < L_unsupported <= 1.524:
            i = 4
        else:
            i = 5
        t = _TEMA_baffles_other[j][i]
    return t



def D_baffle_holes(do=None, L_unsupported=None):
    r'''Determines the diameter of holes in baffles for tubes according to
    TEMA [1]_. Applies for all geometries.

    Parameters
    ----------
    do : float
        Tube outer diameter, [m]
    L_unsupported: float
        Distance between tube supports, [m]

    Returns
    -------
    dB : float
        Baffle hole diameter, [m]

    Notes
    -----

    Examples
    --------
    >>> D_baffle_holes(do=.0508, L_unsupported=0.75)
    0.0516
    >>> D_baffle_holes(do=0.01905, L_unsupported=0.3)
    0.01985
    >>> D_baffle_holes(do=0.01905, L_unsupported=1.5)
    0.019450000000000002

    References
    ----------
    .. [1] Standards of the Tubular Exchanger Manufacturers Association,
       Ninth edition, 2007, TEMA, New York.
    '''
    if do > 0.0318 or L_unsupported <= 0.914: # 1-1/4 inches and 36 inches
        extra = 0.0008
    else:
        extra = 0.0004
    d = do + extra
    return d


_L_unsupported_steel = [0.66, 0.889, 1.118, 1.321, 1.524, 1.753, 1.88, 2.235, 2.54, 3.175, 3.175, 3.175]
_L_unsupported_aluminium = [0.559, 0.762, 0.965, 1.143, 1.321, 1.524, 1.626, 1.93, 2.21, 2.794, 2.794, 2.794]
_L_unsupported_lengths = [0.25, 0.375, 0.5, 0.628, 0.75, 0.875, 1., 1.25, 1.5, 2., 2.5, 3.]

def L_unsupported_max(NPS=None, material='CS'):
    r'''Determines the maximum length of unsupported tube acording to
    TEMA [1]_. Temperature limits are ignored.

    Inputs
    ------
    NPS : float
        Nominal pipe size, [in]
    material: str
        Material type, CS or other for the other list

    Returns
    -------
    L_unsupported : float
        Maximum length of unsupported tube, [m]

    Notes
    -----
    Interpolation of available sizes is probably possible.

    Examples
    --------
    >>> L_unsupported_max(NPS=1.5, material='CS')
    2.54

    References
    ----------
    .. [1] Standards of the Tubular Exchanger Manufacturers Association,
       Ninth edition, 2007, TEMA, New York.
    '''
    if NPS in _L_unsupported_lengths:
        i = _L_unsupported_lengths.index(NPS)
    else:
        raise Exception('Tube size not in list length unsupported list')
    if material == 'CS':
        L = _L_unsupported_steel[i]
    else:
        L = _L_unsupported_aluminium[i]
    return L


### Tube bundle count functions

def Ntubes_Perrys(DBundle=None, do=None, Ntp=None, angle=30):
    r'''A rough equation presented in Perry's Handbook [1]_ for estimating
    the number of tubes in a tube bundle of differing geometries and tube
    sizes. Claimed accuracy of 24 tubes.

    Parameters
    ----------
    DBundle : float
        Outer diameter of tube bundle, [m]
    Ntp : float
        Number of tube passes, [-]
    do : float
        Tube outer diameter, [m]
    angle : float
        The angle the tubes are positioned; 30, 45, 60 or 90

    Returns
    -------
    Nt : float
        Number of tubes, [-]

    Notes
    -----
    Perry's equation 11-74.
    Pitch equal to 1.25 times the tube outside diameter
    No other source for this equation is given.
    Experience suggests this is accurate to 40 tubes, but is often around 20 tubes off.

    Examples
    --------
    >>> [[Ntubes_Perrys(DBundle=1.184, Ntp=i, do=.028, angle=j) for i in [1,2,4,6]] for j in [30, 45, 60, 90]]
    [[1001, 973, 914, 886], [819, 803, 784, 769], [1001, 973, 914, 886], [819, 803, 784, 769]]

    References
    ----------
    .. [1] Green, Don, and Robert Perry. Perry's Chemical Engineers' Handbook,
       Eighth Edition. New York: McGraw-Hill Education, 2007.
    '''
    if angle == 30 or angle == 60:
        C = 0.75*DBundle/do - 36.
        if Ntp == 1:
            Nt = 1298. + 74.86*C + 1.283*C**2 - .0078*C**3 - .0006*C**4
        elif Ntp == 2:
            Nt = 1266. + 73.58*C + 1.234*C**2 - .0071*C**3 - .0005*C**4
        elif Ntp == 4:
            Nt = 1196. + 70.79*C + 1.180*C**2 - .0059*C**3 - .0004*C**4
        elif Ntp == 6:
            Nt = 1166. + 70.72*C + 1.269*C**2 - .0074*C**3 - .0006*C**4
        else:
            raise Exception('N passes not 1, 2, 4 or 6')
    elif angle == 45 or angle == 90:
        C = DBundle/do - 36.
        if Ntp == 1:
            Nt = 593.6 + 33.52*C + .3782*C**2 - .0012*C**3 + .0001*C**4
        elif Ntp == 2:
            Nt = 578.8 + 33.36*C + .3847*C**2 - .0013*C**3 + .0001*C**4
        elif Ntp == 4:
            Nt = 562.0 + 33.04*C + .3661*C**2 - .0016*C**3 + .0002*C**4
        elif Ntp == 6:
            Nt = 550.4 + 32.49*C + .3873*C**2 - .0013*C**3 + .0001*C**4
        else:
            raise Exception('N passes not 1, 2, 4 or 6')
    Nt = int(Nt)
    return Nt




def Ntubes_VDI(DBundle=None, Ntp=None, do=None, pitch=None, angle=30.):
    r'''A rough equation presented in the VDI Heat Atlas for estimating
    the number of tubes in a tube bundle of differing geometries and tube
    sizes. No accuracy estimation given.

    Parameters
    ----------
    DBundle : float
        Outer diameter of tube bundle, [m]
    Ntp : float
        Number of tube passes, [-]
    do : float
        Tube outer diameter, [m]
    pitch : float
        Pitch; distance between two orthogonal tube centers, [m]
    angle : float
        The angle the tubes are positioned; 30, 45, 60 or 90

    Returns
    -------
    Nt : float
        Number of tubes, [-]

    Notes
    -----
    6 tube passes is not officially supported, only 1, 2, 4 and 8.
    However, an estimated constant has been added to support it.
    f2 = 90.
    This equation is a rearranged for of that presented in [1]_.
    Calculated tube count is rounded down to an integer.

    Examples
    --------
    >>> [[Ntubes_VDI(DBundle=1.184, Ntp=i, do=.028, pitch=.036, angle=j) for i in [1,2,4,6,8]] for j in [30, 45, 60, 90]]
    [[983, 966, 929, 914, 903], [832, 818, 790, 778, 769], [983, 966, 929, 914, 903], [832, 818, 790, 778, 769]]

    References
    ----------
    .. [1] Gesellschaft, V. D. I., ed. VDI Heat Atlas. 2nd edition.
       Berlin; New York:: Springer, 2010.
    '''
    if Ntp == 1:
        f2 = 0.
    elif Ntp == 2:
        f2 = 22.
    elif Ntp == 4:
        f2 = 70.
    elif Ntp == 8:
        f2 = 105.
    elif Ntp == 6:
        f2 = 90. # Estimated!
    else:
        raise Exception('Only 1, 2, 4 and 8 passes are supported')


    if angle == 30 or angle == 60:
        f1 = 1.1
    elif angle == 45 or angle == 90:
        f1 = 1.3
    else:
        raise Exception('Only 30, 60, 45 and 90 degree layouts are supported')

    DBundle, do, pitch = DBundle*1000, do*1000, pitch*1000 # convert to mm, equation is dimensional.
    t = pitch
    Ntubes = (-(-4*f1*t**4*f2**2*do + 4*f1*t**4*f2**2*DBundle**2 + t**4*f2**4)**0.5
    - 2*f1*t**2*do + 2*f1*t**2*DBundle**2 + t**2*f2**2) / (2*f1**2*t**4)
    Ntubes = int(Ntubes)
    return Ntubes

#print [[Ntubes_VDI(DBundle=1.184, Ntp=i, do=.028, pitch=.036, angle=j) for i in [1,2,4,6,8]] for j in [30, 45, 60, 90]]

#print [[Ntubes_VDI(DBundle=1.184, Ntp=i, do=.028, pitch=.036, angle=j) for i in [1,2,4,8]] for j in [30, 45, 60, 90]]
#    >>> [Ntubes_Phadkeb(DBundle=1.200-.008*2, do=.028, pitch=.036, Ntp=i, angle=45.) for i in [1,2,4,6,8]]
#    [805, 782, 760, 698, 680]
#








_triangular_Ns = [0, 1, 3, 4, 7, 9, 12, 13, 16, 19, 21, 25, 27, 28, 31, 36, 37, 39, 43, 48, 49, 52, 57, 61, 63, 64, 67, 73, 75, 76, 79, 81, 84, 91, 93, 97, 100, 103, 108, 109, 111, 112, 117, 121, 124, 127, 129, 133, 139, 144, 147, 148, 151, 156, 163, 167, 169, 171, 172, 175, 181, 183, 189, 192, 193, 196, 199, 201, 208, 211, 217, 219, 223, 225, 228, 229, 237, 241, 243, 244, 247, 252, 256, 259, 268, 271, 273, 277, 279, 283, 289, 291, 292, 300, 301, 304, 307, 309, 313, 316, 324, 325, 327, 331, 333, 336, 337, 343, 349, 351, 361, 363, 364, 367, 372, 373, 379, 381, 387, 388, 397, 399, 400, 403, 409, 412, 417, 421, 427, 432, 433, 436, 439, 441, 444, 448, 453, 457, 463, 468, 469, 471, 475, 481, 484, 487, 489, 496, 499, 507, 508, 511, 513, 516, 523, 525, 529, 532, 541, 543, 547, 549, 553, 556, 559, 567, 571, 576, 577, 579, 588, 589, 592, 597, 601, 603, 604, 607, 613, 619, 624, 625, 628, 631, 633, 637, 643, 651, 652, 657, 661, 669, 673, 675, 676, 679, 684, 687, 688, 691, 700, 703, 709, 711, 721, 723, 724, 727, 729, 732, 733, 739, 741, 751, 756, 757, 763, 768, 769, 772, 775, 777, 784, 787, 793, 796, 804, 811, 813, 817, 819, 823, 829, 831, 832, 837, 841, 844, 847, 849, 853, 859, 867, 868, 871, 873, 876, 877, 883, 889, 892, 900, 903, 907, 912, 916, 919, 921, 925, 927, 931, 937, 939, 948, 949, 961, 964, 967, 972, 973, 975, 976, 981, 988, 991, 993, 997, 999]
_triangular_C1s = [1, 7, 13, 19, 31, 37, 43, 55, 61, 73, 85, 91, 97, 109, 121, 127, 139, 151, 163, 169, 187, 199, 211, 223, 235, 241, 253, 265, 271, 283, 295, 301, 313, 337, 349, 361, 367, 379, 385, 397, 409, 421, 433, 439, 451, 463, 475, 499, 511, 517, 535, 547, 559, 571, 583, 595, 613, 625, 637, 649, 661, 673, 685, 691, 703, 721, 733, 745, 757, 769, 793, 805, 817, 823, 835, 847, 859, 871, 877, 889, 913, 925, 931, 955, 967, 979, 1003, 1015, 1027, 1039, 1045, 1057, 1069, 1075, 1099, 1111, 1123, 1135, 1147, 1159, 1165, 1177, 1189, 1201, 1213, 1225, 1237, 1261, 1273, 1285, 1303, 1309, 1333, 1345, 1357, 1369, 1381, 1393, 1405, 1417, 1429, 1453, 1459, 1483, 1495, 1507, 1519, 1531, 1555, 1561, 1573, 1585, 1597, 1615, 1627, 1639, 1651, 1663, 1675, 1687, 1711, 1723, 1735, 1759, 1765, 1777, 1789, 1801, 1813, 1831, 1843, 1867, 1879, 1891, 1903, 1915, 1921, 1945, 1957, 1969, 1981, 1993, 2017, 2029, 2053, 2065, 2077, 2083, 2095, 2107, 2125, 2149, 2161, 2173, 2185, 2197, 2209, 2221, 2233, 2245, 2257, 2263, 2275, 2287, 2299, 2335, 2347, 2371, 2383, 2395, 2407, 2419, 2431, 2437, 2455, 2479, 2491, 2503, 2515, 2527, 2539, 2563, 2575, 2587, 2611, 2623, 2635, 2647, 2653, 2665, 2677, 2689, 2713, 2725, 2737, 2749, 2773, 2779, 2791, 2803, 2815, 2839, 2857, 2869, 2893, 2905, 2917, 2929, 2941, 2965, 2989, 3001, 3013, 3025, 3037, 3049, 3055, 3067, 3079, 3091, 3103, 3115, 3121, 3145, 3169, 3181, 3193, 3205, 3217, 3241, 3253, 3259, 3283, 3295, 3307, 3319, 3331, 3343, 3355, 3367, 3403, 3415, 3427, 3439, 3463, 3481, 3493, 3505, 3511, 3535, 3547, 3559, 3571, 3595, 3607, 3619, 3631, 3643]
Phadkeb_triangular = interp1d(_triangular_Ns, _triangular_C1s, copy=False, kind='zero')
_square_Ns = [0, 1, 2, 4, 5, 8, 9, 10, 13, 16, 17, 18, 20, 25, 26, 29, 32, 34, 36, 37, 40, 41, 45, 49, 50, 52, 53, 58, 61, 64, 65, 68, 72, 73, 74, 80, 81, 82, 85, 89, 90, 97, 98, 100, 101, 104, 106, 109, 113, 116, 117, 121, 122, 125, 128, 130, 136, 137, 144, 145, 146, 148, 149, 153, 157, 160, 162, 164, 169, 170, 173, 178, 180, 181, 185, 193, 194, 196, 197, 200, 202, 205, 208, 212, 218, 221, 225, 226, 229, 232, 233, 234, 241, 242, 244, 245, 250, 256, 257, 260, 261, 265, 269, 272, 274, 277, 281, 288, 289, 290, 292, 293, 296, 298, 305, 306, 313, 314, 317, 320, 324, 325, 328, 333, 337, 338, 340, 346, 349, 353, 356, 360, 361, 362, 365, 369, 370, 373, 377, 386, 388, 389, 392, 394, 397, 400, 401, 404, 405, 409, 410, 416, 421, 424, 425, 433, 436, 441, 442, 445, 449, 450, 452, 457, 458, 461, 464, 466, 468, 477, 481, 482, 484, 485, 488, 490, 493, 500, 505, 509, 512, 514, 520, 521, 522, 529, 530, 533, 538, 541, 544, 545, 548, 549, 554, 557, 562, 565, 569, 576, 577, 578, 580, 584, 585, 586, 592, 593, 596, 601, 605, 610, 612, 613, 617, 625, 626, 628, 629, 634, 637, 640, 641, 648, 650, 653, 656, 657, 661, 666, 673, 674, 676, 677, 680, 685, 689, 692, 697, 698, 701, 706, 709, 712, 720, 722, 724, 725, 729, 730, 733, 738, 740, 745, 746, 754, 757, 761, 765, 769, 772, 773, 776, 778, 784, 785, 788, 793, 794, 797, 800, 801, 802, 808, 809, 810, 818, 820, 821, 829, 832, 833, 841, 842, 845, 848, 850, 853, 857, 865, 866, 872, 873, 877, 881, 882, 884, 890, 898, 900, 901, 904, 905, 909, 914, 916, 922, 925, 928, 929, 932, 936, 937, 941, 949, 953, 954, 961, 962, 964, 965, 968, 970, 976, 977, 980, 981, 985, 986, 997, 1000]
_square_C1s = [1, 5, 9, 13, 21, 25, 29, 37, 45, 49, 57, 61, 69, 81, 89, 97, 101, 109, 113, 121, 129, 137, 145, 149, 161, 169, 177, 185, 193, 197, 213, 221, 225, 233, 241, 249, 253, 261, 277, 285, 293, 301, 305, 317, 325, 333, 341, 349, 357, 365, 373, 377, 385, 401, 405, 421, 429, 437, 441, 457, 465, 473, 481, 489, 497, 506, 509, 517, 529, 545, 553, 561, 569, 577, 593, 601, 609, 613, 621, 633, 641, 657, 665, 673, 681, 697, 709, 717, 725, 733, 741, 749, 757, 761, 769, 777, 793, 797, 805, 821, 829, 845, 853, 861, 869, 877, 885, 889, 901, 917, 925, 933, 941, 949, 965, 973, 981, 989, 997, 1005, 1009, 1033, 1041, 1049, 1057, 1069, 1085, 1093, 1101, 1109, 1117, 1125, 1129, 1137, 1153, 1161, 1177, 1185, 1201, 1209, 1217, 1225, 1229, 1237, 1245, 1257, 1265, 1273, 1281, 1289, 1305, 1313, 1321, 1329, 1353, 1361, 1369, 1373, 1389, 1405, 1413, 1425, 1433, 1441, 1449, 1457, 1465, 1473, 1481, 1489, 1505, 1513, 1517, 1533, 1541, 1549, 1565, 1581, 1597, 1605, 1609, 1617, 1633, 1641, 1649, 1653, 1669, 1685, 1693, 1701, 1709, 1725, 1733, 1741, 1749, 1757, 1765, 1781, 1789, 1793, 1801, 1813, 1829, 1837, 1853, 1861, 1869, 1877, 1885, 1893, 1901, 1917, 1925, 1933, 1941, 1961, 1969, 1977, 1993, 2001, 2009, 2017, 2025, 2029, 2053, 2061, 2069, 2077, 2085, 2093, 2101, 2109, 2121, 2129, 2145, 2161, 2177, 2185, 2201, 2209, 2217, 2225, 2233, 2241, 2249, 2253, 2261, 2285, 2289, 2305, 2313, 2321, 2337, 2353, 2361, 2377, 2385, 2393, 2409, 2417, 2425, 2433, 2441, 2449, 2453, 2469, 2477, 2493, 2501, 2509, 2521, 2529, 2537, 2545, 2553, 2561, 2569, 2585, 2593, 2601, 2609, 2617, 2629, 2637, 2661, 2669, 2693, 2701, 2709, 2725, 2733, 2741, 2749, 2757, 2765, 2769, 2785, 2801, 2809, 2812, 2837, 2845, 2861, 2869, 2877, 2885, 2893, 2917, 2925, 2933, 2941, 2949, 2957, 2965, 2981, 2989, 2997, 3001, 3017, 3025, 3041, 3045, 3061, 3069, 3077, 3085, 3093, 3109, 3125, 3133, 3149]
Phadkeb_square = interp1d(_square_Ns, _square_C1s, copy=False, kind='zero')


def Ntubes_Phadkeb(DBundle=None, Ntp=None, do=None, pitch=None, angle=30):
    r'''Using tabulated values and correction factors for number of passes,
    the highly accurate method of [1]_ is used to obtain the tube count
    of a given tube bundle outer diameter for a given tube size and pitch.

    Parameters
    ----------
    DBundle : float
        Outer diameter of tube bundle, [m]
    Ntp : float
        Number of tube passes, [-]
    do : float
        Tube outer diameter, [m]
    pitch : float
        Pitch; distance between two orthogonal tube centers, [m]
    angle : float
        The angle the tubes are positioned; 30, 45, 60 or 90

    Returns
    -------
        Nt : float
            Number of tubes, [-]

    Notes
    -----
    This function will fail when there are more than several thousand tubes.
    This is due to a limitation in tabulated values presented in [1]_.

    Examples
    --------
    >>> [Ntubes_Phadkeb(DBundle=1.200-.008*2, do=.028, pitch=.036, Ntp=i, angle=45.) for i in [1,2,4,6,8]]
    [805, 782, 760, 698, 680]
    >>> [Ntubes_Phadkeb(DBundle=1.200-.008*2, do=.028, pitch=.035, Ntp=i, angle=45.) for i in [1,2,4,6,8]]
    [861, 838, 816, 750, 732]

    References
    ----------
    .. [1] Phadke, P. S., Determining tube counts for shell and tube
       exchangers, Chem. Eng., September, 91, 65-68 (1984).
    '''
    if Ntp == 6:
        e = 0.265
    elif Ntp == 8:
        e = 0.404
    else:
        e = 0

    r = 0.5*(DBundle-do)/pitch
    s = r**2
    Ns, Nr = floor(s), floor(r)
    if angle == 30 or angle == 60:
        C1 = Phadkeb_triangular(Ns)
    elif angle == 45 or angle == 90:
        C1 = Phadkeb_square(Ns)

    Cx = 2*Nr + 1

    # triangular and rotated triangular
    if (angle == 30 or angle == 60):
        w = 2*r/3**0.5
        Nw = floor(w)
        if Nw % 2 == 0:
            Cy = 3*Nw
        else:
            Cy = 3*Nw + 1
        if Ntp == 2:
            if angle == 30 :
                C2 = C1 - Cx
            else:
                C2 = C1 - Cy - 1
        else: # 4 passes, or 8; this value is needed
            C4 = C1 - Cx - Cy

    if (angle == 30 or angle == 60) and (Ntp == 6 or Ntp == 8):
        if angle == 30: # triangular
            v = 2*e*r/3**0.5 + 0.5
            Nv = floor(v)
            u = 3**0.5*Nv/2.
            if Nv %2 == 0:
                z = (s-u**2)**0.5
            else:
                z = (s-u**2)**0.5 - 0.5
            Nz = floor(z)
            if Ntp == 6:
                C6 = C1 - Cy - 4*Nz - 1
            else:
                C8 = C4 - 4*Nz
        else: # rotated triangular
            v = 2*e*r
            Nv = floor(v)
            u1 = 0.5*Nv
            z = (s-u1**2)**0.5
            w1 = 2**2**0.5
            u2 = 0.5*(Nv + 1)
            zs = (s-u2**2)**0.5
            w2 = 2*zs/3**0.5
            if Nv%2 == 0:
                z1 = 0.5*w1
                z2 = 0.5*(w2+1)
            else:
                z1 = 0.5*(w1+1)
                z2 = 0.5*w2
            Nz1 = floor(z1)
            Nz2 = floor(z2)
            if Ntp == 6:
                C6 = C1 - Cx - 4*(Nz1 + Nz2)
            else: # 8
                C8 = C4-4*(Nz1 + Nz2)

    if (angle == 45 or angle == 90):
        if angle == 90:
            Cy = Cx - 1
            # eq 6 or 8 for c2 or c4
            if Ntp == 2:
                C2 = C1 - Cx
            else: # 4 passes, or 8; this value is needed
                C4 = C1 - Cx - Cy
        else: # rotated square
            w = r/2**0.5
            Nw = floor(w)
            Cx = 2*Nw + 1
            Cy = Cx - 1
            if Ntp == 2:
                C2 = C1 - Cx
            else: # 4 passes, or 8; this value is needed
                C4 = C1 - Cx - Cy

    if (angle == 45 or angle == 90) and (Ntp == 6 or Ntp == 8):
        if angle == 90:
            v = e*r + 0.5
            Nv = floor(v)
            z = (s - Nv**2)**0.5
            Nz = floor(z)
            if Ntp == 6:
                C6 = C1 - Cy - 4*Nz - 1
            else:
                C8 = C4 - 4*Nz
        else:
            w = r/2**0.5
            Nw = floor(w)
            Cx = 2*Nw + 1

            v = 2**0.5*e*r
            Nv = floor(v)
            u1 = Nv/2**0.5
            z = (s-u1**2)**0.5
            w1 = 2**0.5*z
            u2 = (Nv + 1)/2**0.5
            zs = (s-u2**2)**0.5
            w2 = 2**0.5*zs
            # if Nv is odd, 21a and 22a. If even, 21b and 22b. Nz1, Nz2
            if Nv %2 == 0:
                z1 = 0.5*w1
                z2 = 0.5*(w2 + 1)
            else:
                z1 = 0.5*(w1 + 1)
                z2 = 0.5*w2
            Nz1 = floor(z1)
            Nz2 = floor(z2)
            if Ntp == 6:
                C6 = C1 - Cx - 4*(Nz1 + Nz2)
            else: # 8
                C8 = C4-4*(Nz1 + Nz2)


    if Ntp == 1:
        return int(C1)
    elif Ntp == 2:
        return int(C2)
    elif Ntp == 4:
        return int(C4)
    elif Ntp == 6:
        return int(C6)
    else:
        return int(C8)


#print Ntubes_Phadkeb(Dshell=1.00, do=.0135, pitch=.025, Ntp=1, angle=30.), 'good'
#print [Ntubes_Phadkeb(Dshell=1.200-.008*2, do=.028, pitch=.035, Ntp=i, angle=90.) for i in [1,2,4,6,8]]
#print [Ntubes_Phadkeb(DBundle=1.200-.008*2, do=.028, pitch=.036, Ntp=i, angle=45.) for i in [1,2,4,6,8]]



#print [[Ntubes_Phadkeb(DBundle=1.200-.008*2, do=.028, pitch=.028*1.25, Ntp=i, angle=j) for i in [1,2,4,6,8]] for j in [30, 45, 60, 90]]


def Ntubes_HEDH(DBundle=None, do=None, pitch=None, angle=30):
    r'''A rough equation presented in the HEDH for estimating
    the number of tubes in a tube bundle of differing geometries and tube
    sizes. No accuracy estimation given. Only 1 pass is supported.

    Parameters
    ----------
    DBundle : float
        Outer diameter of tube bundle, [m]
    do : float
        Tube outer diameter, [m]
    pitch : float
        Pitch; distance between two orthogonal tube centers, [m]
    angle : float
        The angle the tubes are positioned; 30, 45, 60 or 90

    Returns
    -------
    Nt : float
        Number of tubes, [-]

    Notes
    -----
    Seems highly accurate.

    Examples
    --------
    >>> [Ntubes_HEDH(DBundle=1.200-.008*2, do=.028, pitch=.036, angle=i) for i in [30, 45, 60, 90]]
    [928, 804, 928, 804]

    References
    ----------
    .. [1] Schlunder, Ernst U, and International Center for Heat and Mass
       Transfer. Heat Exchanger Design Handbook. Washington:
       Hemisphere Pub. Corp., 1983.
    '''
    if angle == 30 or angle == 60:
        C1 = 13/15.
    elif angle == 45 or angle == 90:
        C1 = 1.
    else:
        raise Exception('Only 30, 60, 45 and 90 degree layouts are supported')
    Dctl = DBundle-do
    Nt = 0.78*Dctl**2/C1/pitch**2
    Nt = int(Nt)
    return Nt


def Ntubes(DBundle=None, Ntp=1, do=None, pitch=None, angle=30, pitch_ratio=1.25, AvailableMethods=False, Method=None):
    '''Function to calculate the number of tubes which can fit in a given tube
    bundle outer diameter.

    >>> Ntubes(DBundle=1.2, do=0.025)
    1285
    '''
    def list_methods():
        methods = []
        methods.append('Phadkeb')
        if Ntp == 1:
            methods.append('HEDH')
        if Ntp == 1 or Ntp == 2 or Ntp == 4 or Ntp == 8:
            methods.append('VDI')
        if Ntp == 1 or Ntp == 2 or Ntp == 4 or Ntp == 6: # Also restricted to 1.25 pitch ratio but not hard coded
            methods.append("Perry's")
        methods.append('None')
        return methods
    if AvailableMethods:
        return list_methods()
    if not Method:
        Method = list_methods()[0]

    if pitch_ratio and not pitch:
        pitch = pitch_ratio*do
    if Method == 'Phadkeb':
        N = Ntubes_Phadkeb(DBundle=DBundle, Ntp=Ntp, do=do, pitch=pitch, angle=angle)
    elif Method == 'HEDH':
        N = Ntubes_HEDH(DBundle=DBundle, do=do, pitch=pitch, angle=angle)
    elif Method == 'VDI':
        N = Ntubes_VDI(DBundle=DBundle, Ntp=Ntp, do=do, pitch=pitch, angle=angle)
    elif Method == "Perry's":
        N = Ntubes_Perrys(DBundle=DBundle, do=do, Ntp=Ntp, angle=angle)
    elif Method == 'None':
        return None
    else:
        raise Exception('Failure in in function')
    return N


def D_for_Ntubes_VDI(Nt=None, Ntp=None, do=None, pitch=None, angle=30):
    r'''A rough equation presented in the VDI Heat Atlas for estimating
    the size of a tube bundle from a given number of tubes, number of tube
    passes, outer tube diameter, pitch, and arrangement.
    No accuracy estimation given.

    .. math::
        OTL = \sqrt{f_1 z t^2 + f_2 t \sqrt{z} - d_o}

    Parameters
    ----------
    Nt : float
        Number of tubes, [-]
    Ntp : float
        Number of tube passes, [-]
    do : float
        Tube outer diameter, [m]
    pitch : float
        Pitch; distance between two orthogonal tube centers, [m]
    angle : float
        The angle the tubes are positioned; 30, 45, 60 or 90

    Returns
    -------
    DBundle : float
        Outer diameter of tube bundle, [m]

    Notes
    -----
    f1 = 1.1 for triangular, 1.3 for square patterns
    f2 is as follows: 1 pass, 0; 2 passes, 22; 4 passes, 70; 8 passes, 105.
    6 tube passes is not officially supported, only 1, 2, 4 and 8.
    However, an estimated constant has been added to support it.
    f2 = 90.

    Examples
    --------
    >>> D_for_Ntubes_VDI(Nt=970, Ntp=2., do=0.00735, pitch=0.015, angle=30.)
    0.5003600119829544

    References
    ----------
    .. [1] Gesellschaft, V. D. I., ed. VDI Heat Atlas. 2nd edition.
       Berlin; New York:: Springer, 2010.
    '''
    if Ntp == 1:
        f2 = 0.
    elif Ntp == 2:
        f2 = 22.
    elif Ntp == 4:
        f2 = 70.
    elif Ntp == 6:
        f2 = 90.
    elif Ntp == 8:
        f2 = 105.
    else:
        raise Exception('Only 1, 2, 4 and 8 passes are supported')
    if angle == 30 or angle == 60:
        f1 = 1.1
    elif angle == 45 or angle == 90:
        f1 = 1.3
    else:
        raise Exception('Only 30, 60, 45 and 90 degree layouts are supported')
    do, pitch = do*1000, pitch*1000 # convert to mm, equation is dimensional.
    Dshell = (f1*Nt*pitch**2 + f2*Nt**0.5*pitch +do)**0.5
    Dshell = Dshell/1000.
    return Dshell


TEMA_heads = {'A': 'Removable Channel and Cover', 'B': 'Bonnet (Integral Cover)', 'C': 'Integral With Tubesheet Removable Cover', 'N': 'Channel Integral With Tubesheet and Removable Cover', 'D': 'Special High-Pressure Closures'}
TEMA_shells = {'E': 'One-Pass Shell', 'F': 'Two-Pass Shell with Longitudinal Baffle', 'G': 'Split Flow', 'H': 'Double Split Flow', 'J': 'Divided Flow', 'K': 'Kettle-Type Reboiler',  'X': 'Cross Flow'}
TEMA_rears = {'L': 'Fixed Tube Sheet; Like "A" Stationary Head', 'M': 'Fixed Tube Sheet; Like "B" Stationary Head', 'N': 'Fixed Tube Sheet; Like "C" Stationary Head', 'P': 'Outside Packed Floating Head', 'S': 'Floating Head with Backing Device', 'T': 'Pull-Through Floating Head', 'U': 'U-Tube Bundle', 'W': 'Externally Sealed Floating Tubesheet'}
TEMA_services = {'B': 'Chemical', 'R': 'Refinery', 'C': 'General'}
baffle_types = ['segmental', 'double segmental', 'triple segmental', 'disk and doughnut', 'no tubes in window', 'orifice', 'rod']
