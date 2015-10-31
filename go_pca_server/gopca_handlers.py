import os
import stat
import shutil
import subprocess as subproc

import tornado.web
from handlers import TemplateHandler
from items import GSRun
import util

class GOPCAHandler(TemplateHandler):

    def initialize(self,data):
        super(GOPCAHandler,self).initialize(data)

    @property
    def run_dir(self):
        return self.config['run_dir']

    @property
    def data_dir(self):
        return self.config['data_dir']

    @property
    def max_file_size(self):
        return self.config['max_file_size']

    @property
    def species_names(self):
        return self.data['species_names']

    def validate_post_data(self):
        # make sure here that everything is kosher, otherwise give an error saying "invalid data" or something
        # e.g., evidence codes need to be checked

        # make sure expression file URL has valid format
        return True

    def post(self):

        if not self.validate_post_data():
            return

        session_id = self.generate_session_id()

        if session_id in self.runs:
            # very unlikely
            # TO-DO: error! Run ID already exists.
            return

        self.set_secure_cookie('session_id',session_id)
        #self.write(session_id)

        species = self.get_body_argument('species')
        description = self.get_body_argument('description',default='')

        r = GSRun(session_id,GSRun.get_current_time(),self.run_dir,species,description)
        self.logger.debug('Created run %s',str(r))

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
                expression_url = expression_url,
                max_file_size = max_file_size,
                gene_annotation_file = gene_annotation_file,
                gene_ontology_file = gene_ontology_file,
                go_association_file = go_association_file,
                go_evidence = evidence,
                go_min_genes = min_genes,
                go_max_genes = max_genes)
        output_file = run_dir + os.sep + 'gopca.sh'
        with open(output_file,'w') as ofh:
            ofh.write(script)
        self.logger.debug('Wrote file "%s".',output_file)

        # run the script
        st = os.stat(output_file)
        os.chmod(output_file, st.st_mode | stat.S_IXUSR)
        log_file = run_dir + os.sep + 'gopca_log.txt'
        cmd = '"%s" > "%s" 2>&1' %(output_file,log_file)
        self.logger.debug('Command: %s',cmd)
        subproc.Popen(cmd,shell=True,executable='/bin/bash')

        # update run status
        r.update_status()
        r.store_data()

        # write html
        template = self.get_template('submit.html')
        html_output = template.render(timestamp=self.ts,title='Submission',run_id=session_id)
        self.write(html_output)

        self.runs[session_id] = r

class DeleteRunHandler(TemplateHandler):

    def initialize(self,data):
        super(DeleteRunHandler,self).initialize(data)

    @property
    def run_dir(self):
        return self.config['run_dir']

    def post(self):
        template = self.get_template('delete_run.html')
        run_id = self.get_body_argument('run_id')
        self.logger.debug('Delete-run run-id: %s', run_id)
        self.logger.debug('Delete-run runs: %s', ', '.join(sorted(self.data['runs'].keys())))
        try:
            # delete the run
            del self.data['runs'][run_id]
        except KeyError:
            pass
            #self.data['runs'].remove(run_id)
        else:
            # the ID existed => it should be safe to remove the directory
            run_dir = self.run_dir + os.sep + run_id
            self.logger.debug('Deleting directory "%s".', run_dir)
            shutil.rmtree(run_dir,ignore_errors=True)
            # also delete session cookie if it points to the deleted run
            session_id = self.get_secure_cookie('session_id')
            if session_id is not None and session_id == run_id:
                self.clear_cookie('session_id')
            self.logger.debug('Deleted run with ID "%s".', run_id)
        #html_output = template.render(timestamp=self.ts,title='Delete run - GOPCA Server',run_id=run_id)
        #self.write(html_output)
        #tornado.ioloop.IOLoop.instance().call_later(10,self.redirect,'/?new=1')
