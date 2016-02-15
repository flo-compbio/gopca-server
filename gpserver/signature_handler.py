import os
import stat
import shutil
import subprocess as subproc
import io

import tornado.web
from handlers import GSHandler
from items import GSRun
import util

import numpy as np

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
#import matplotlib.image as mpimg
from matplotlib import rc
#from matplotlib import cm

#from gopca.go_pca_objects import GOPCAConfig
from gopca import util

class SignatureHandler(GSHandler):

    def initialize(self,data):
        super(SignatureHandler,self).initialize(data)

    def get_signature_by_hash(self,signatures,h):
        for s in signatures:
            if hash(s) == h: return s
        return None

    @property
    def run_dir(self):
        return self.config['run_dir']

    def get_signature_plot(self,S,sig,fig_size=(15,10),font_size=16,dpi=150,vmin=-3.0,vmax=3.0):
        # S = signature matrix

        # get signature gene expression matrix and cluster rows
        sig_genes = sig.genes
        E = sig.E
        order_rows = util.cluster_rows(E, metric = 'correlation', method = 'average')
        sig_genes = [sig_genes[i] for i in order_rows]
        E = E[order_rows,:]

        # standardize gene expression matrix
        E_std = util.get_standardized_matrix(E)
        # calculate signature label and expression
        sig_label = sig.get_label(include_id=True)
        sig_expr = np.mean(E_std,axis=0)

        # get sample order from signature matrix
        order_cols = util.cluster_samples(S)
        sig_expr = sig_expr[order_cols]
        E_std = E_std[:,order_cols]

        # plotting
        rc('font',family='serif',size=font_size)
        rc('figure',figsize=(fig_size[0],fig_size[1]))
        rc('savefig',dpi=dpi)

        # subgrid layout
        ax = plt.subplot2grid((10,1),(0,0))
        plt.sca(ax)

        plt.imshow(np.atleast_2d(sig_expr),aspect='auto',interpolation='none',vmin=vmin,vmax=vmax,cmap='RdBu_r')
        plt.xticks(())
        plt.yticks([0],['Signature'],size='small')

        ax = plt.subplot2grid((10,1),(1,0),rowspan=10-1)
        plt.sca(ax)
        plt.imshow(E_std,interpolation='none',aspect='auto',vmin=vmin,vmax=vmax,cmap='RdBu_r')
        plt.yticks(np.arange(len(sig_genes)),sig_genes,size='x-small')
        plt.xlabel('Samples')
        plt.ylabel('Genes')
        plt.xticks(())

        minint = int(vmin)
        maxint = int(vmax)
        cbticks = np.arange(minint,maxint+0.01,1.0)
        #cb = plt.colorbar(orientation=fig_cbar_orient,shrink=fig_cbar_shrink,pad=fig_cbar_pad,ticks=cbticks,use_gridspec=False,anchor=fig_cbar_anchor)
        cb = plt.colorbar(orientation='horizontal',ticks=cbticks,use_gridspec=False,anchor=(0.85,1.8),shrink=0.3)
        cb.ax.tick_params(labelsize='small')
        cb.set_label('Standardized Expression',size='small')
        plt.suptitle(sig_label,va='bottom',y=0.92)

        memdata = io.BytesIO()

        plt.savefig(memdata, format = 'png', bbox_inches = 'tight')
        image = memdata.getvalue()

        return image


    def get(self,run_id,signature_id):
        gopca_file = self.run_dir + os.sep + run_id + os.sep + 'gopca_result.pickle'
        self.debug('GOA-PCA file: %s', gopca_file)
        G = util.read_gopca_result(gopca_file)
        sig = self.get_signature_by_hash(G.signatures, int(signature_id))

        if sig is None:
            raise tornado.web.HTTPError(404)

        self.debug('Signature: %s', str(sig))

        image = self.get_signature_plot(G.S, sig)
        self.set_header('Content-type', 'image/png')
        self.set_header('Content-length', len(image))
        self.write(image)
