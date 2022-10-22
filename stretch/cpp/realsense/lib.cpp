#include "lib.h"

namespace stretch::realsense {

int device_count() {
    rs2::context ctx;
    return ctx.query_devices().size();
}

int main() try {
    rs2::pipeline p;
    std::cout << "a\n";
    p.start();
    std::cout << "b\n";
    while (true) {
        std::cout << "c\n";
        rs2::frameset frames = p.wait_for_frames();
        std::cout << "d\n";
        rs2::depth_frame depth = frames.get_depth_frame();
        std::cout << "e\n";
        auto width = depth.get_width();
        std::cout << "f\n";
        auto height = depth.get_height();
        std::cout << "g\n";
        float dist_to_center = depth.get_distance(width / 2, height / 2);
        std::cout << "The camera is facing an object " << dist_to_center << " meters away \r";
    }
    return EXIT_SUCCESS;
} catch (const rs2::error& e) {
    std::cerr << "RealSense error calling " << e.get_failed_function() << "(" << e.get_failed_args() << "):\n    "
              << e.what() << std::endl;
    return EXIT_FAILURE;
} catch (const std::exception& e) {
    std::cerr << "True exception:" << e.what() << std::endl;
    return EXIT_FAILURE;
}

PYBIND11_MODULE(lib, m) {
    m.def("device_count", &device_count);
    m.def("test_realsense_device", &main);
}

}  // namespace stretch::realsense
