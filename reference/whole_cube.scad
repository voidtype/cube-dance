corner_extra_width = 4.1;
stick_height = 200;
corner_cube_height = 30;

difference(){
    cube(stick_height + 2*corner_cube_height);
    translate([0,corner_cube_height,corner_cube_height]){
        cube([stick_height+2*corner_cube_height,stick_height,stick_height]);
    }
    translate([corner_cube_height,0,corner_cube_height]){
        cube([stick_height,stick_height+2*corner_cube_height,stick_height]);
    }
    translate([corner_cube_height,corner_cube_height,0]){
        cube([stick_height,stick_height,stick_height+2*corner_cube_height]);
    }
}
translate([-corner_extra_width,-corner_extra_width,0]){
    cube(corner_cube_height+corner_extra_width);
}
translate([-corner_extra_width,stick_height+corner_cube_height,0]){
    cube(corner_cube_height+corner_extra_width);
}
translate([stick_height+corner_cube_height,-corner_extra_width,0]){
    cube(corner_cube_height+corner_extra_width);
}
translate([stick_height+corner_cube_height,stick_height+corner_cube_height,0]){
    cube(corner_cube_height+corner_extra_width);
}
translate([-corner_extra_width,-corner_extra_width,stick_height+corner_cube_height]){
    cube(corner_cube_height+corner_extra_width);
}
translate([-corner_extra_width,stick_height+corner_cube_height,stick_height+corner_cube_height]){
    cube(corner_cube_height+corner_extra_width);
}
translate([stick_height+corner_cube_height,-corner_extra_width,stick_height+corner_cube_height]){
    cube(corner_cube_height+corner_extra_width);
}
translate([stick_height+corner_cube_height,stick_height+corner_cube_height,stick_height+corner_cube_height]){
    cube(corner_cube_height+corner_extra_width);
}