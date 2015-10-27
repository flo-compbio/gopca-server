import os
import shutil

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

	def post(self):
		session_id = self.get_body_argument('session_id')
		if session_id is None:
			# TO-DO: check that this is a hash!
			return # no session ID provided
		
		if session_id in self.runs:
			# TO-DO: error! Run ID already exists.
			return

		self.set_secure_cookie('session_id',session_id)
		self.write(session_id)
		r = GSRun(session_id)
		self.runs[session_id] = r

		# create the directory
		# 
		run_dir = self.run_dir + os.sep + session_id
		print 'Creating directory "%s"...' %(run_dir)
		util.make_sure_path_exists(run_dir)

class DeleteRunHandler(TemplateHandler):

	def initialize(self,data):
		super(DeleteRunHandler,self).initialize(data)

	@property
	def run_dir(self):
		return self.config['run_dir']

	def post(self):
		template = self.get_template('delete_run.html')
		run_id = self.get_body_argument('run_id')
		print 'Delete-run run-id: %s' %(run_id)
		print 'Delete-run runs: %s' %(', '.join(sorted(self.data['runs'].keys())))
		try:
			# delete the run
			del self.data['runs'][run_id]
		except KeyError:
			pass
			#self.data['runs'].remove(run_id)
		else:
			# the ID existed => it should be safe to remove the directory
			run_dir = self.run_dir + os.sep + run_id
			print 'Deleting directory "%s".' %(run_dir)
			shutil.rmtree(run_dir,ignore_errors=True)
			# also delete session cookie if it points to the deleted run
			session_id = self.get_secure_cookie('session_id')
			if session_id is not None and session_id == run_id:
				self.clear_cookie('session_id')
			print 'Deleted run with ID "%s".' %(run_id)
		#html_output = template.render(timestamp=self.ts,title='Delete run - GOPCA Server',run_id=run_id)
		#self.write(html_output)
		#tornado.ioloop.IOLoop.instance().call_later(10,self.redirect,'/?new=1')
