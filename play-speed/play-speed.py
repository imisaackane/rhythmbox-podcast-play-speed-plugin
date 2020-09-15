from gi.repository import GObject, Peas, Gst, Gtk, RB

import gettext
gettext.install('rhythmbox', RB.locale_dir())

class PlaySpeedAudjuster(GObject.Object, Peas.Activatable):
	__gtype_name = 'PlaySpeedAudjusterPlugin'
	object = GObject.property(type=GObject.GObject)

	rate_list = [['0.5x', 0.5], ['0.75x', 0.75], ['1x', 1], ['1.25x', 1.25], ['1.5x', 1.5], ['1.75x', 1.75], ['2x', 2]]

	is_podcast = False
	has_duration = False
	connected_audio_bin = False

	previous_elapsed = 0
	rate = 1.75
	
	shell = None
	audio_bin = None
	playbin = None

	podcast_control_tool_items = []

	def __init__(self):
		GObject.Object.__init__(self)
			
	def do_activate(self):
		print("Activating PlaySpeedAudjuster")
		self.shell = self.object
		self.audio_bin = self.create_audio_bin()
		self.create_display()
		self.destroy_display()

		self.shell.props.shell_player.connect('playing-source-changed', self.source_changed)
		self.shell.props.shell_player.connect('playing-song-changed', self.song_changed)
		self.shell.props.shell_player.connect('elapsed-changed', self.elapsed_changed)

	def source_changed(self, shell_player, source):
		if source == None:
			return

		self.is_podcast = 'podcast' in source.props.entry_type.get_name() or 'Podcast' in source.props.entry_type.get_name()
		self.update_display()

	def song_changed(self, shell_player, entry):
		self.try_setup_playbin()
		if not self.connected_audio_bin:
			self.connect_audio_bin_to_playbin()
			self.refresh_source(entry)
		
		self.has_duration = self.playbin.query_duration(Gst.Format.TIME).duration > 0
		self.previous_elapsed = self.playbin.query_position(Gst.Format.TIME).cur/1000000000
		self.update_play_speed()

	def rate_changed(self, combobox):
		self.rate = self.rate_list[combobox.props.active][1]
		self.update_play_speed()	

	def elapsed_changed(self, shell_player, elapsed):
		if abs(self.previous_elapsed - elapsed) >  + 2:
			self.update_play_speed()  
		self.previous_elapsed = elapsed

	def display_elements_added(self, container, added):
		self.print(added)

	def create_audio_bin (self):
		audio_line = Gst.Bin.new('audioline')
		
		scale_tempo_element = Gst.ElementFactory.make('scaletempo', 'scaletempo')
		convert_element = Gst.ElementFactory.make('audioconvert', 'convert')
		resample_element = Gst.ElementFactory.make('audioresample', 'resample')
		alsa_sink_element = Gst.ElementFactory.make('alsasink', 'audiosink')

		audio_line.add(scale_tempo_element)
		audio_line.add(convert_element)
		audio_line.add(resample_element)
		audio_line.add(alsa_sink_element)
		
		scale_tempo_element.link(convert_element)
		convert_element.link(resample_element)
		resample_element.link(alsa_sink_element)

		sink_pad = scale_tempo_element.sinkpads[0]
		audio_line.add_pad(Gst.GhostPad.new('sink', sink_pad))

		return audio_line

	def connect_audio_bin_to_playbin(self):
		if self.playbin == None:
			print("Cannot connect Audio Line to Playbin, playbin does not exist")
			return

		print(self.audio_bin)
		
		self.playbin.set_property('audio-sink', self.audio_bin)
		self.connected_audio_bin = True
		

	def refresh_source(self, entry):
		shell_player = self.shell.props.shell_player
		current_source = shell_player.props.source
		shell_player.stop()
		shell_player.play_entry(entry, current_source)

	def update_play_speed(self):
		if not self.can_be_speed_up():
			print("Cannot update speed on current song/configuration")
			return
		
		position = self.playbin.query_position(Gst.Format.TIME).cur
		duration = self.playbin.query_duration(Gst.Format.TIME).duration

		seek_results = self.playbin.seek(self.rate, Gst.Format.TIME, Gst.SeekFlags.FLUSH, Gst.SeekType.SET, position, Gst.SeekType.SET, duration)
		
		if seek_results:
			print('Rate successfully changed to: ' + str(self.rate))
		else:
			print('Playbin would not accept rate change')

	def can_be_speed_up(self):
		return self.is_podcast and self.can_be_speed_up

	def try_setup_playbin(self):
		if self.playbin == None:
			playbin = self.shell.props.shell_player.props.player.props.playbin
			if playbin == None:
				print('could not setup playbin')
			else:
				self.playbin = playbin
				print('playbin setup successful')
		
	def create_display(self):
		window_contents = self.shell.props.window.get_child()
		toolbars = self.recursive_toolbar_search(window_contents, 0)
		for toolbar in toolbars:
			self.add_toolbar_items(toolbar)
			if toolbar.props.visible:
				toolbar.show_all()

	def add_toolbar_items(self, toolbar):
		new_tool_item = Gtk.ToolItem.new()
		combo_box = self.create_rate_change_box ()
		combo_box.connect('changed', self.rate_changed)
		#TODO: Jump ahead
		#TODO: Jump back
		
		new_tool_item.add(combo_box)
		self.podcast_control_tool_items.append(new_tool_item)

		toolbar.insert(new_tool_item, 2)

	def create_rate_change_box(self):
		new_combo_box = Gtk.ComboBoxText.new()
		for i in self.rate_list:
			new_combo_box.append_text(i[0])
		new_combo_box.set_active(2)
		return new_combo_box

	def destroy_display(self):
		for tool_item in self.podcast_control_tool_items:
			tool_item.destroy()
		self.podcast_control_tool_items = []

	def recursive_toolbar_search(self, GtkObj, depth):
		current_toolbars = []
		if GtkObj is not None and hasattr(GtkObj, 'get_children'):
			for child in GtkObj.get_children():
				if child.get_name() == 'GtkToolbar':
					current_toolbars.append(child)
				else:
					current_toolbars.extend(self.recursive_toolbar_search(child, depth+1))
		return current_toolbars

	def update_display(self):
		print('updating_display', self.is_podcast, len(self.podcast_control_tool_items))
		if self.is_podcast and len(self.podcast_control_tool_items) == 0:
			self.create_display()
		elif not self.is_podcast and len(self.podcast_control_tool_items) != 0:
			self.destroy_display()
			
	def do_deactivate(self):
		print("Dectivating PlaySpeedAudjuster")