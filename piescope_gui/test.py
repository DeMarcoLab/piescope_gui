import correlateim.main as corr

input_filename_1 = "C:\\Users\\David\\images\\worm_fluorescence-microscopy.tif"
input_filename_2 = "C:\\Users\\David\\images\\worm_ion-beam-microscopy-tilted.tif"
output_filename = "C:\\Users\\David\\images\\output.tiff"
corr.correlate_images(input_filename_1, input_filename_2, output_filename)