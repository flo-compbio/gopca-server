import tornado.web
from handlers import TemplateHandler
from items import GSRun

class GOPCAHandler(TemplateHandler):

	def initialize(self,data):
		super(GOPCAHandler,self).initialize(data)

	def post(self):
		session_id = self.get_body_argument('session_id')
		self.set_secure_cookie('session_id',session_id)
		self.write(session_id)
		r = GSRun(session_id)
		self.runs[session_id] = r

class DeleteRunHandler(TemplateHandler):

	def initialize(self,data):
		super(DeleteRunHandler,self).initialize(data)

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
			print 'Deleted run with ID "%s".' %(run_id)
			# also delete session cookie if it points to the deleted run
			session_id = self.get_secure_cookie('session_id')
			if session_id is not None and session_id == run_id:
				self.clear_cookie('session_id')
		#html_output = template.render(timestamp=self.ts,title='Delete run - GOPCA Server',run_id=run_id)
		#self.write(html_output)
		#tornado.ioloop.IOLoop.instance().call_later(10,self.redirect,'/?new=1')
