#include "lib.h"

namespace stretch::realsense {

int device_count() {
    rs2::context ctx;
    return ctx.query_devices().size();
}

class VideoFrame {
   private:
    rs2::video_frame rs_frame;

   public:
    VideoFrame(const rs2::video_frame& rs_frame) : rs_frame(std::move(rs_frame)) {}

    const uint8_t* data() const { return (uint8_t*)rs_frame.get_data(); }
    const int rows() const { return std::max(rs_frame.get_height(), 0); }
    const int cols() const { return std::max(rs_frame.get_width(), 0); }
    const int bytes_per_pixel() const { return rs_frame.get_bytes_per_pixel(); }
};

class Frame {
   public:
    VideoFrame rgb;

    Frame(const VideoFrame& rgb) : rgb(std::move(rgb)) {}
};

class FrameGenerator {
   private:
    rs2::pipeline* pipe;

   public:
    FrameGenerator() : pipe(nullptr) {}

    ~FrameGenerator() {
        if (this->pipe != nullptr) this->pipe->stop();
    }

    const FrameGenerator* iter() {
        this->pipe = new rs2::pipeline();
        this->pipe->start();
        return this;
    }

    const Frame* next() {
        if (this->pipe == nullptr)
            throw std::runtime_error("`pipe` hasn't been initialized; must call `__iter__` first");
        rs2::frameset frames = this->pipe->wait_for_frames();
        VideoFrame video_frame(frames.get_color_frame());
        Frame* frame = new Frame(video_frame);
        return frame;
    }
};

PYBIND11_MODULE(lib, m) {
    m.def("device_count", &device_count);

    pybind11::class_<VideoFrame>(m, "VideoFrame", pybind11::buffer_protocol())
        .def_buffer([](VideoFrame& m) -> pybind11::buffer_info {
            auto buf = pybind11::buffer_info(m.data(), sizeof(uint8_t), true);
            buf.format = pybind11::format_descriptor<uint8_t>::format();
            buf.ndim = 3;
            buf.shape = {m.rows(), m.cols(), m.bytes_per_pixel()};
            buf.strides = {m.cols() * m.bytes_per_pixel(), m.bytes_per_pixel(), 1};
            return buf;
        })
        .def_property_readonly("rows", &VideoFrame::rows)
        .def_property_readonly("cols", &VideoFrame::cols)
        .def_property_readonly("bytes_per_pixel", &VideoFrame::bytes_per_pixel);

    pybind11::class_<Frame>(m, "Frame").def_readonly("rgb", &Frame::rgb);

    pybind11::class_<FrameGenerator>(m, "FrameGenerator")
        .def(pybind11::init<>())
        .def("__iter__", &FrameGenerator::iter)
        .def("__next__", &FrameGenerator::next);
}

}  // namespace stretch::realsense
