from __init__ import *

import os

import matplotlib.pyplot as plt
import numpy as np

from astropy.table import Table, vstack
from scipy.interpolate import CloughTocher2DInterpolator, LinearNDInterpolator
from scipy.interpolate import griddata, interp1d

import dynesty
from dynesty import plotting as dyplot
from dynesty import utils as dyfunc

dirpath = os.path.dirname(__file__)

def interpolate_2d(x, y, z, method):
    if method == 'linear':
        interpolator = LinearNDInterpolator
    elif method == 'cubic':
        interpolator = CloughTocher2DInterpolator
    return interpolator((x,y), z, rescale=True)
    #return interp2d(x, y, z, kind=method)


def interp_atm(atm_type, color, logteff_logg_grid=(3.5, 5.1, 0.01, 6.5, 9.6, 0.01), 
               interp_type_atm='linear'):
    """interpolate the mapping (logteff, logg) --> photometry
    
    This function interpolates the mapping (logteff, logg) --> color index or
    bolometric correction (BC) of a passband.
    
    Args:
        atm_type:           String. {'H', 'He'}
            See the "Synthetic color" section on http://www.astro.umontreal.ca/~bergeron/CoolingModels/
        color:              String. {'G-Mbol', 'bp-rp', 'V-Mbol', 'u-g', 'B-z', etc.}
            The target color of the mapping. Any two bands between 
            Gaia: G, bp, rp
            SDSS: Su, Sg, Sr, Si, Sz
            PanSTARRS: Pg, Pr, Pi, Pz, Py
            Johnson: U, B, V, R, I
            2MASS: J, H, Ks
            Mauna Kea Observatory (MKO): MY, MJ, MH, MK
            WISE: W1, W2, W3, W4
            Spitzer: S36, S45, S58, S80
            GALEX: FUV, NUV
            and the bolometric magnitude: Mbol.
            For bolometric correction (BC), 'Mbol' must be the passband after
            the minus sign '-'.
        logteff_logg_grid: (xmin, xmax, dx, ymin, ymax, dy). *Optional*
            corresponding to the grid of logTeff and logg.
        interp_type_atm:    String. {'linear', 'cubic'}. *Optional*
            Linear is much better for our purpose.
    
    Returns:
        grid_atm:           2d-array. 
                            The value of photometry on a (logteff, logg) grid
        atm_func:           Function. 
                            The interpolated mapping function:
                                (logteff, logg) --> photometry
        
    """
    logteff     = np.zeros(0) # atmospheric parameter
    logg        = np.zeros(0) # atmospheric parameter
    Mbol        = np.zeros(0) # Bolometric
    bp_Mag      = np.zeros(0) # Gaia
    rp_Mag      = np.zeros(0) # Gaia 
    G_Mag       = np.zeros(0) # Gaia
    Su_Mag      = np.zeros(0) # SDSS
    Sg_Mag      = np.zeros(0) # SDSS
    Sr_Mag      = np.zeros(0) # SDSS
    Si_Mag      = np.zeros(0) # SDSS
    Sz_Mag      = np.zeros(0) # SDSS
    Pg_Mag      = np.zeros(0) # PanSTARRS
    Pr_Mag      = np.zeros(0) # PanSTARRS
    Pi_Mag      = np.zeros(0) # PanSTARRS
    Pz_Mag      = np.zeros(0) # PanSTARRS
    Py_Mag      = np.zeros(0) # PanSTARRS
    U_Mag       = np.zeros(0) # Johnson
    B_Mag       = np.zeros(0) # Johnson
    V_Mag       = np.zeros(0) # Johnson
    R_Mag       = np.zeros(0) # Johnson
    I_Mag       = np.zeros(0) # Johnson
    J_Mag       = np.zeros(0) # 2MASS
    H_Mag       = np.zeros(0) # 2MASS
    Ks_Mag      = np.zeros(0) # 2MASS
    MY_Mag      = np.zeros(0) # Mauna Kea Observatory (MKO)
    MJ_Mag      = np.zeros(0) # Mauna Kea Observatory (MKO)
    MH_Mag      = np.zeros(0) # Mauna Kea Observatory (MKO)
    MK_Mag      = np.zeros(0) # Mauna Kea Observatory (MKO)
    W1_Mag      = np.zeros(0) # WISE
    W2_Mag      = np.zeros(0) # WISE
    W3_Mag      = np.zeros(0) # WISE
    W4_Mag      = np.zeros(0) # WISE
    S36_Mag     = np.zeros(0) # Spitzer IRAC
    S45_Mag     = np.zeros(0) # Spitzer IRAC
    S58_Mag     = np.zeros(0) # Spitzer IRAC
    S80_Mag     = np.zeros(0) # Spitzer IRAC
    FUV_Mag     = np.zeros(0) # GALEX
    NUV_Mag     = np.zeros(0) # GALEX 
    
    # read the table for all logg
    if atm_type == 'H':
        suffix = 'DA'
    if atm_type == 'He':
        suffix = 'DB'
    Atm_color = Table.read(dirpath+'/Montreal_atm_grid_2019/Table_'+suffix,
                           format='ascii')
    selected  = Atm_color['Teff'] > 10**logteff_logg_grid[0]
    Atm_color = Atm_color[selected]

    table_95 = Atm_color[-51:].copy()
    table_95['logg'] = 9.5
    table_95['M/Mo'] = 1.366
    for column in ['Mbol','U','B','V','R','I','J','H','Ks','MY','MJ','MH','MK','W1','W2','W3','W4',
         'S3.6','S4.5','S5.8','S8.0','Su','Sg','Sr','Si','Sz','Pg','Pr','Pi','Pz','Py',
         'G','G_BP','G_RP','FUV','NUV']:
        table_95[column] += 1.108
    Atm_color = vstack(( Atm_color, table_95 ))
    
    selected  = Atm_color['Teff'] > 10**logteff_logg_grid[0]
    Atm_color = Atm_color[selected]
    
    # read columns from the Table_DA and Table_DB files
    logteff = np.concatenate(( logteff, np.log10(Atm_color['Teff']) ))
    logg    = np.concatenate(( logg, Atm_color['logg'] ))
    Mbol    = np.concatenate(( Mbol, Atm_color['Mbol'] ))
    bp_Mag  = np.concatenate(( bp_Mag, Atm_color['G_BP'] ))
    rp_Mag  = np.concatenate(( rp_Mag, Atm_color['G_RP'] ))
    G_Mag   = np.concatenate(( G_Mag, Atm_color['G'] ))
    Su_Mag  = np.concatenate(( Su_Mag, Atm_color['Su'] ))
    Sg_Mag  = np.concatenate(( Sg_Mag, Atm_color['Sg'] ))
    Sr_Mag  = np.concatenate(( Sr_Mag, Atm_color['Sr'] ))
    Si_Mag  = np.concatenate(( Si_Mag, Atm_color['Si'] ))
    Sz_Mag  = np.concatenate(( Sz_Mag, Atm_color['Sz'] ))
    Pg_Mag  = np.concatenate(( Pg_Mag, Atm_color['Pg'] ))
    Pr_Mag  = np.concatenate(( Pr_Mag, Atm_color['Pr'] ))
    Pi_Mag  = np.concatenate(( Pi_Mag, Atm_color['Pi'] ))
    Pz_Mag  = np.concatenate(( Pz_Mag, Atm_color['Pz'] ))
    Py_Mag  = np.concatenate(( Py_Mag, Atm_color['Py'] ))
    U_Mag   = np.concatenate(( U_Mag, Atm_color['U'] ))
    B_Mag   = np.concatenate(( B_Mag, Atm_color['B'] ))
    V_Mag   = np.concatenate(( V_Mag, Atm_color['V'] ))
    R_Mag   = np.concatenate(( R_Mag, Atm_color['R'] ))
    I_Mag   = np.concatenate(( I_Mag, Atm_color['I'] ))
    J_Mag   = np.concatenate(( J_Mag, Atm_color['J'] ))
    H_Mag   = np.concatenate(( H_Mag, Atm_color['H'] ))
    Ks_Mag  = np.concatenate(( Ks_Mag, Atm_color['Ks'] ))
    MY_Mag  = np.concatenate(( MY_Mag, Atm_color['MY'] ))
    MJ_Mag  = np.concatenate(( MJ_Mag, Atm_color['MJ'] ))
    MH_Mag  = np.concatenate(( MH_Mag, Atm_color['MH'] ))
    MK_Mag  = np.concatenate(( MK_Mag, Atm_color['MK'] ))
    W1_Mag  = np.concatenate(( W1_Mag, Atm_color['W1'] ))
    W2_Mag  = np.concatenate(( W2_Mag, Atm_color['W2'] ))
    W3_Mag  = np.concatenate(( W3_Mag, Atm_color['W3'] ))
    W4_Mag  = np.concatenate(( W4_Mag, Atm_color['W4'] ))
    S36_Mag = np.concatenate(( S36_Mag, Atm_color['S3.6'] ))
    S45_Mag = np.concatenate(( S45_Mag, Atm_color['S4.5'] ))
    S58_Mag = np.concatenate(( S58_Mag, Atm_color['S5.8'] ))
    S80_Mag = np.concatenate(( S80_Mag, Atm_color['S8.0'] ))
    FUV_Mag = np.concatenate(( FUV_Mag, Atm_color['FUV'] ))
    NUV_Mag = np.concatenate(( NUV_Mag, Atm_color['NUV'] ))
        
    # define the interpolation of mapping
    def interp(x, y, z, interp_type_atm='linear'):
        # grid_z      = griddata(np.array((x, y)).T, z, (grid_x, grid_y),
        #                         method=interp_type_atm)
        z_func      = interpolate_2d(x, y, z, interp_type_atm)
        return z_func
    
    if isinstance(color, (list, tuple, np.ndarray)):
        pass
    else:
        color = [color]
    
    z = np.zeros((len(color), len(logg)))
    for idx, clr in enumerate(color):
        z[idx, :] = eval(clr + '_Mag')
    
    return interp(logteff, logg, z.T, interp_type_atm)


class FitSED:
    
    def __init__(self, atm_type, bands = ['G', 'bp', 'rp']):
        self.interpolator = interp_atm(atm_type, bands)
        self.teff_range = [4000, 100_000]
        self.logg_range = [6.5, 9.5]
        self.bands = bands
        self.atm_type = atm_type
        
    def model_sed(self, teff, logg):
        logteff = np.log10(teff)
        
        return self.interpolator(logteff, logg)
    
    def prior_transform(self, u):
        x = np.array(u)
        x[0] = u[0] * (self.teff_range[1] - self.teff_range[0]) + self.teff_range[0]
        x[1] = u[1] * (self.logg_range[1] - self.logg_range[0]) + self.logg_range[0]
        return x
    
    def fit_sed(self, sed, e_sed, nlive = 250,
                plot_fit = True, plot_trace = False, plot_corner = False, progress = False):
        
        def loglike(theta):
            teff, logg = theta
            model = self.model_sed(teff, logg)
            ivar = 1 / e_sed**2
            logchi =  -0.5 * np.sum((sed - model)**2 * ivar)
            if np.isnan(logchi):
                return -np.Inf
            else:
                return logchi
        
        dsampler = dynesty.NestedSampler(loglike, self.prior_transform, ndim=2,
                                        nlive = nlive)
        dsampler.run_nested(print_progress = progress)
        
        result = dsampler.results

        samples, weights = result.samples, np.exp(result.logwt - result.logz[-1])
        mean, cov = dyfunc.mean_and_cov(samples, weights)

        model = self.model_sed(*mean)
            
        ivar = 1 / e_sed**2
        redchi = np.sum((sed - model)**2 * ivar) / (len(sed) - 2)

        
        if plot_trace:

            f = dyplot.traceplot(dsampler.results, show_titles = True, 
                             trace_cmap = 'viridis')
            plt.tight_layout()
        if plot_corner:
        
            f = dyplot.cornerplot(dsampler.results, show_titles = True)
            
        if plot_fit:
            
            plt.figure(figsize = (8,5))
            plt.errorbar(self.bands, sed, yerr = e_sed, linestyle = 'none', capsize = 5, color = 'k')
            plt.scatter(self.bands, model, color = 'k')
            plt.text(0.15, 0.3, '$T_{\mathrm{eff}}$ = %i ± %i' %(mean[0], np.sqrt(cov[0,0])), transform = plt.gca().transAxes)
            plt.text(0.15, 0.25, '$\log{g}$ = %.2f ± %.2f' %(mean[1], np.sqrt(cov[1,1])), transform = plt.gca().transAxes)
            plt.text(0.15, 0.2, 'atm = %s' %(self.atm_type), transform = plt.gca().transAxes)
            plt.text(0.15, 0.15, '$\chi_r^2$ = %.2f' %(redchi), transform = plt.gca().transAxes)
            plt.xlabel('Passband', fontsize = 16)
            plt.ylabel('$M_{x}$', fontsize = 16)
            plt.gca().invert_yaxis()
            
        return [mean[0], np.sqrt(cov[0,0]), mean[1], np.sqrt(cov[1,1])], redchi

if __name__ == '__main__':
    
    
    fitsed = FitSED('H', bands = ['Su', 'Sg', 'Sr', 'Si', 'Sz'])
    
    obs = fitsed.model_sed(15000, 8)
    obs += 0.01 * np.random.normal(size = len(obs))
    e_obs = 0.01
    
    # plt.plot(obs, 'k.')
    
    # print(fitsed.prior_transform(np.array([np.linspace(0, 1, 100), np.linspace(0, 1, 100)])))
    
    fitsed.fit_sed(obs, e_obs, nlive = 250)
    