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

class ColorFrame {
   protected:
    rs2_frame* frame;

   public:
    ColorFrame(rs2_frame* frames, int frame_id) {
        rs2_error* e = 0;
        frame = rs2_extract_frame(frames, frame_id, &e);
        check_error(e);
    }

    ~ColorFrame() { rs2_release_frame(frame); }

    const uint8_t* data() const {
        rs2_error* e = 0;
        auto data = (const uint8_t*)(rs2_get_frame_data(frame, &e));
        check_error(e);
        return data;
    }

    const int width() const {
        rs2_error* e = 0;
        auto frame_width = rs2_get_frame_width(frame, &e);
        check_error(e);
        return frame_width;
    }

    const int height() const {
        rs2_error* e = 0;
        auto frame_height = rs2_get_frame_height(frame, &e);
        check_error(e);
        return frame_height;
    }

    const int bytes_per_pixel() const { return 3; }

    const unsigned long long frame_number() const {
        rs2_error* e = 0;
        auto frame_number = rs2_get_frame_number(frame, &e);
        check_error(e);
        return frame_number;
    }

    const rs2_time_t frame_timestamp() const {
        rs2_error* e = 0;
        auto frame_timestamp = rs2_get_frame_timestamp(frame, &e);
        check_error(e);
        return frame_timestamp;
    }
};

class ColorFrameGenerator {
   private:
    size_t device_id;
    rs2_context* ctx;
    rs2_device_list* device_list;
    rs2_device* dev;
    rs2_pipeline* pipeline;
    rs2_config* config;
    rs2_pipeline_profile* pipeline_profile;
    rs2_frame* frames;
    rs2_frame* frame;
    int num_frames;
    int frame_id;

   public:
    ColorFrameGenerator(size_t device_id = 0) : device_id(device_id), frame_id(0) {
        rs2_error* e = 0;
        ctx = rs2_create_context(RS2_API_VERSION, &e);
        check_error(e);
        device_list = rs2_query_devices(ctx, &e);
        check_error(e);
        int dev_count = rs2_get_device_count(device_list, &e);
        check_error(e);
        if (static_cast<int>(device_id) >= dev_count) {
            std::ostringstream ss;
            ss << "Device ID " << device_id << " is out-of-bounds since only " << dev_count
               << "device(s) are connected";
            throw std::runtime_error(ss.str());
        }
        dev = rs2_create_device(device_list, device_id, &e);
        check_error(e);
        pipeline = rs2_create_pipeline(ctx, &e);
        check_error(e);
        config = rs2_create_config(&e);
        check_error(e);
        rs2_config_enable_stream(config, RS2_STREAM_COLOR, 0, /* width */ 640, /* height */ 480, RS2_FORMAT_RGB8,
                                 /* fps */ 30, &e);
        check_error(e);
        pipeline_profile = rs2_pipeline_start_with_config(pipeline, config, &e);
        check_error(e);
        frames = rs2_pipeline_wait_for_frames(pipeline, RS2_DEFAULT_TIMEOUT, &e);
        check_error(e);
        num_frames = rs2_embedded_frames_count(frames, &e);
        check_error(e);
        if (num_frames <= 0) throw std::runtime_error("Didn't get any frames");
        frame = rs2_extract_frame(frames, frame_id++, &e);
        check_error(e);
    }

    ~ColorFrameGenerator() {
        rs2_error* e = 0;
        rs2_release_frame(frame);
        rs2_release_frame(frames);
        rs2_pipeline_stop(pipeline, &e);
        check_error(e);
        rs2_delete_pipeline_profile(pipeline_profile);
        rs2_delete_config(config);
        rs2_delete_pipeline(pipeline);
        rs2_delete_device(dev);
        rs2_delete_device_list(device_list);
        rs2_delete_context(ctx);
    }

    const ColorFrameGenerator* iter() { return this; }

    const ColorFrame* next() {
        rs2_release_frame(frame);
        rs2_error* e = 0;
        while (frame_id >= num_frames) {
            rs2_release_frame(frames);
            frames = rs2_pipeline_wait_for_frames(pipeline, RS2_DEFAULT_TIMEOUT, &e);
            check_error(e);
            num_frames = rs2_embedded_frames_count(frames, &e);
            check_error(e);
            frame_id = 0;
        }
        return new ColorFrame(frames, frame_id++);
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

    pybind11::class_<ColorFrameGenerator>(m, "ColorFrameGenerator")
        .def(pybind11::init<>())
        .def("__iter__", &ColorFrameGenerator::iter)
        .def("__next__", &ColorFrameGenerator::next);
}

}  // namespace stretch::realsense
