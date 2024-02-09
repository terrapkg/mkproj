project pkg {
	rpm {
		spec = ""
		enable_scm = true
		scm_opts = {
			method = "git"
			package = "{{ name }}"
			branch = "{{ branch }}"
			write_tar = "true"
			spec = "{{ spec }}"
			git_get = "git clone {{ url }}"
		}
	}
}
