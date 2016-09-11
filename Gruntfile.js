module.exports = function(grunt) {

  // Project configuration.
  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),
    image_resize: {
    dev: {
      options: {
          engine: 'im',
            width: 100,
            height: 150,
            overwrite: true,
            upscale: true,
            // crop: true
        },
      files: [{
        expand: true,
        src: ['*.{jpg,png,jpeg}'],
        cwd: 'static/images/',
        dest: 'static/images/'
      }]
    }
  },
  });

  grunt.loadNpmTasks('grunt-image-resize');
  grunt.registerTask('default',['image_resize']);

};
