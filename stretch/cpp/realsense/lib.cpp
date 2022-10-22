#include "lib.h"

namespace stretch::realsense {

int device_count() {
    rs2::context ctx;
    return ctx.query_devices().size();
}

PYBIND11_MODULE(lib, m) { m.def("device_count", &device_count); }

}  // namespace stretch::realsense
