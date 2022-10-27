#include "lib.h"

namespace stretch::realsense {

int device_count() {
    rs2::context ctx;
    return ctx.query_devices().size();
}

void check_error(rs2_error* e) {
    if (e) {
        std::ostringstream ss;
        ss << "Error raised while calling " << rs2_get_failed_function(e) << "(" << rs2_get_failed_args(e) << "):\n   "
           << rs2_get_error_message(e);
        throw std::runtime_error(ss.str());
    }
}

template <class frame_t, typename data_t>
class BaseFrame {
   protected:
    frame_t frame;

   public:
    BaseFrame(frame_t& frame) : frame(std::forward<frame_t>(frame)) {}

    const data_t* data() const { return (const data_t*)frame.get_data(); }
    const int width() const { return frame.get_width(); }
    const int height() const { return frame.get_height(); }
    const int bytes_per_pixel() const { return frame.get_bytes_per_pixel() / sizeof(data_t); }
    const unsigned long long frame_number() const { return frame.get_frame_number(); }
    const rs2_time_t frame_timestamp() const { return frame.get_timestamp(); }
};

class ColorFrame : public BaseFrame<rs2::video_frame, uint8_t> {
   public:
    ColorFrame(rs2::video_frame& frame) : BaseFrame(frame) {}
};

class DepthFrame : public BaseFrame<rs2::depth_frame, uint8_t> {
   public:
    DepthFrame(rs2::depth_frame& frame) : BaseFrame(frame) {}

    const float units() const { return frame.get_units(); }
};

class FrameSet {
   public:
    ColorFrame rgb;
    DepthFrame depth;

    FrameSet(rs2::video_frame& rgb, rs2::depth_frame& depth) : rgb(rgb), depth(depth) {}
};

class FrameGenerator {
   private:
    rs2::pipeline pipe;

   public:
    FrameGenerator(size_t device_id = 0) {
        // Gets the correct device.
        rs2::context ctx;
        auto device_list = ctx.query_devices();
        auto device_count = device_list.size();
        if (device_id >= device_count) {
            std::ostringstream ss;
            ss << "Device ID " << device_id << " is out-of-bounds since only " << device_count
               << "device(s) are connected";
            throw std::runtime_error(ss.str());
        }
        auto device = device_list[device_id];

        // Creates a new pipeline.
        pipe = rs2::pipeline(ctx);
        rs2::config cfg;
        cfg.enable_stream(RS2_STREAM_COLOR, 0, /* width */ 640, /* height */ 480, RS2_FORMAT_YUYV, /* fps */ 30);
        cfg.enable_stream(RS2_STREAM_DEPTH, 0, /* width */ 640, /* height */ 480, RS2_FORMAT_Z16, /* fps */ 30);
        pipe.start(cfg);
    }

    const FrameGenerator* iter() { return this; }

    const FrameSet* next() {
        auto frames = pipe.wait_for_frames();
        auto color_frame = frames.get_color_frame();
        auto depth_frame = frames.get_depth_frame();
        return new FrameSet(color_frame, depth_frame);
    }
};

using namespace pybind11::literals;

PYBIND11_MODULE(lib, m) {
    m.def("device_count", &device_count);

    pybind11::class_<rs2_quaternion>(m, "Quaternion")
        .def_readonly("x", &rs2_quaternion::x)
        .def_readonly("y", &rs2_quaternion::y)
        .def_readonly("z", &rs2_quaternion::z)
        .def_readonly("w", &rs2_quaternion::w);

    pybind11::class_<rs2_vector>(m, "Vector")
        .def_readonly("x", &rs2_vector::x)
        .def_readonly("y", &rs2_vector::y)
        .def_readonly("z", &rs2_vector::z);

    pybind11::class_<ColorFrame>(m, "ColorFrame", pybind11::buffer_protocol())
        .def_buffer([](ColorFrame& m) -> pybind11::buffer_info {
            auto buf = pybind11::buffer_info(m.data(), sizeof(uint8_t), true);
            buf.format = pybind11::format_descriptor<uint8_t>::format();
            buf.ndim = 3;
            buf.shape = {m.height(), m.width(), m.bytes_per_pixel()};
            buf.strides = {m.width() * m.bytes_per_pixel(), m.bytes_per_pixel(), 1};
            return buf;
        })
        .def_property_readonly("width", &ColorFrame::width)
        .def_property_readonly("height", &ColorFrame::height)
        .def_property_readonly("bytes_per_pixel", &ColorFrame::bytes_per_pixel)
        .def_property_readonly("frame_number", &ColorFrame::frame_number)
        .def_property_readonly("frame_timestamp", &ColorFrame::frame_timestamp);

    pybind11::class_<DepthFrame>(m, "DepthFrame", pybind11::buffer_protocol())
        .def_buffer([](DepthFrame& m) -> pybind11::buffer_info {
            auto buf = pybind11::buffer_info(m.data(), sizeof(uint8_t), true);
            buf.format = pybind11::format_descriptor<uint8_t>::format();
            buf.ndim = 3;
            buf.shape = {m.height(), m.width(), m.bytes_per_pixel()};
            buf.strides = {m.width() * m.bytes_per_pixel(), m.bytes_per_pixel(), 1};
            return buf;
        })
        .def_property_readonly("width", &DepthFrame::width)
        .def_property_readonly("height", &DepthFrame::height)
        .def_property_readonly("bytes_per_pixel", &DepthFrame::bytes_per_pixel)
        .def_property_readonly("frame_number", &DepthFrame::frame_number)
        .def_property_readonly("frame_timestamp", &DepthFrame::frame_timestamp)
        .def_property_readonly("units", &DepthFrame::units);

    pybind11::class_<FrameSet>(m, "Frame").def_readonly("rgb", &FrameSet::rgb).def_readonly("depth", &FrameSet::depth);

    pybind11::class_<FrameGenerator>(m, "FrameGenerator")
        .def(pybind11::init<>())
        .def("__iter__", &FrameGenerator::iter)
        .def("__next__", &FrameGenerator::next);
}

}  // namespace stretch::realsense
