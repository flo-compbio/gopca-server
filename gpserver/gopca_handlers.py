import os
import stat
import shutil
import logging
import codecs
import subprocess as subproc

import tornado.web
from handlers import GSHandler
from items import GSRun
import util

from gopca import GOPCAConfig

logger = logging.getLogger(__name__)

class GOPCAHandler(GSHandler):

    def initialize(self,data):
        super(GOPCAHandler, self).initialize(data)

    #@property
    #def run_dir(self):
    #    return self.config['run_dir']

    #@property
    #def data_dir(self):
    #    return self.config['data_dir']

    #@property
    #def max_file_size(self):
    #    return self.config['max_file_size']

    def validate_post_data(self):
        # make sure here that everything is kosher, otherwise give an error saying "invalid data" or something
        # e.g., evidence codes need to be checked
        # TO-DO!!!

        # make sure expression file URL has valid format
        return True

    def get_gopca_config_from_post_data(self):
        params = {}
        params['sel_var_genes'] = int(self.get_body_argument('sel_var_genes'))
        params['n_components'] = int(self.get_body_argument('n_components'))
        params['pc_seed'] = int(self.get_body_argument('pc_seed'))
        params['pc_permutations'] = int(self.get_body_argument('pc_permutations'))
        params['pc_zscore_thresh'] = float(self.get_body_argument('pc_zscore_thresh'))
        params['pval_thresh'] = float(self.get_body_argument('pval_thresh'))
        params['sig_corr_thresh'] = float(self.get_body_argument('sig_corr_thresh'))
        params['mHG_X_frac'] = float(self.get_body_argument('mHG_X_frac'))
        params['mHG_X_min'] = int(self.get_body_argument('mHG_X_min'))
        params['mHG_L'] = int(self.get_body_argument('mHG_L'))
        params['escore_pval_thresh'] = float(self.get_body_argument('psi'))
        params['escore_thresh'] = float(self.get_body_argument('escore_thresh'))
        params['disable_local_filter'] = (self.get_body_argument('disable_local',default=0) != 0)
        params['disable_global_filter'] = (self.get_body_argument('disable_global',default=0) != 0)
        params['go_part_of_cc_only'] = \
                (self.get_body_argument('go_part_of_cc_only', default=0) != 0)
        C = GOPCAConfig(params)
        return C

    def post(self):

        # validate data first
        if not self.validate_post_data():
            return

        gopca_config = self.get_gopca_config_from_post_data()
        #gopca_config.validate()
        # write config to a ini file

        # generate job ID
        job_id = ''
        while not job_id:
            job_id = self.generate_session_id()

            if job_id in self.jobs:
                # very unlikely
                job_id = ''

        #self.set_secure_cookie('session_id',session_id)
        #self.write(session_id)

        #self.logger.debug('Value of disable_local: %s', self.get_body_argument('disable_local',default=0))
        #self.logger.debug('Value of disable_global: %s', self.get_body_argument('disable_global',default=0))

        species = self.get_body_argument('species')
        description = self.get_body_argument('description',default='')

        job = GSJob(session_id, GSJob.get_current_time(),self.run_dir,species,description)
        self.logger.debug('Created job %s', str(job))

        # create the directory
        run_dir = self.run_dir + os.sep + session_id
        self.logger.debug('GOPCAHandler: Creating directory "%s"...', run_dir)
        util.make_sure_path_exists(run_dir)

        # store run data
        r.store_data()

        # create bash file
        species_name = self.species_names[species]
        gene_annotation_file = self.data_dir + os.sep + self.get_body_argument('gene_annotation') + '.gtf.gz'

        expression_url = self.get_body_argument('expression')

        go_annotation = self.get_body_argument('go_annotation')
        gene_ontology_file = self.data_dir + os.sep + go_annotation + '.obo'
        go_association_file = self.data_dir + os.sep + go_annotation + '.gaf.gz'

        evidence = self.get_body_arguments('go_evidence')
        min_genes = str(int(self.get_body_argument('go_min_genes')))
        max_genes = str(int(self.get_body_argument('go_max_genes')))
        self.logger.debug('Evidence: %s', str(evidence))
        #evidence_str = ' '.join(['"%s"' %(str(e)) for e in evidence])

        #def esc(fn):
        #    return fn.replace(' ',r'\ ')

        max_file_size = int(self.max_file_size * 1e6)
        template = self.get_template('gopca.sh')
        script = template.render(
                species_name = species_name,
                # expression data
                expression_url = expression_url,
                max_file_size = max_file_size,
                # Gene annotations
                gene_annotation_file = gene_annotation_file,
                # GO annotations
                gene_ontology_file = gene_ontology_file,
                go_association_file = go_association_file,
                go_evidence = evidence,
                go_min_genes = min_genes,
                go_max_genes = max_genes,
                # GO-PCA
                gopca_config = gopca_config
                )
        assert isinstance(script, unicode)
        output_file = run_dir + os.sep + 'gopca.sh'
        with codecs.open(output_file, 'wb', encoding = 'utf-8') as ofh:
            ofh.write(script)
        self.logger.debug('Wrote file "%s".',output_file)

        # run the script
        st = os.stat(output_file)
        os.chmod(output_file, st.st_mode | stat.S_IXUSR)
        log_file = run_dir + os.sep + 'gopca_pipeline_log.txt'
        cmd = '"%s" > "%s" 2>&1' %(output_file, log_file)
        logger.debug('Command: %s', cmd)
        subproc.Popen(cmd, shell = True, executable = '/bin/bash')

        # update run status
        r.update_status()
        r.store_data()

        # write html
        template = self.get_template('submit.html')
        html_output = template.render(timestamp=self.ts,title='Submission',run_id=session_id)
        self.write(html_output)

        self.runs[session_id] = r

class DeleteJobHandler(GSHandler):

    def initialize(self, data):
        super(DeleteJobHandler, self).initialize(data)

    @property
    def job_dir(self):
        return self.config['job_dir']

    def post(self):
        template = self.get_template('delete_job.html')
        job_id = self.get_body_argument('job_id')
        logger.debug('Delete-job with ID "%s"', run_id)
        logger.debug('Delete-job jobs: %s',
                ', '.join(sorted(self.data['jobs'].keys())))
        try:
            # delete the run
            del self.data['jobs'][job_id]
        except KeyError:
            pass
        else:
            # the ID existed => it should be safe to remove the directory
            dir_ = self.job_dir + os.sep + job_id
            logger.debug('Deleting directory "%s".', dir_)
            shutil.rmtree(dir_, ignore_errors = True)
            # also delete session cookie if it points to the deleted run
            logger.debug('Deleted run with ID "%s".', run_id)
        #html_output = template.render(timestamp=self.ts,title='Delete run - GOPCA Server',run_id=run_id)
        #self.write(html_output)
        #tornado.ioloop.IOLoop.instance().call_later(10,self.redirect,'/?new=1')
