#include "lib.h"

namespace stretch::realsense {

int device_count() {
    rs2::context ctx;
    return ctx.query_devices().size();
}

class VideoFrame {
   protected:
    rs2::video_frame rs_frame;

   public:
    VideoFrame(rs2::video_frame rs_frame) : rs_frame(std::forward<rs2::video_frame>(rs_frame)) {}

    const uint8_t* data() const { return (uint8_t*)rs_frame.get_data(); }
    const int rows() const { return std::max(rs_frame.get_height(), 0); }
    const int cols() const { return std::max(rs_frame.get_width(), 0); }
    const int bytes_per_pixel() const { return rs_frame.get_bytes_per_pixel(); }
};

class DepthFrame {
   protected:
    rs2::depth_frame rs_frame;

   public:
    DepthFrame(rs2::depth_frame rs_frame) : rs_frame(std::forward<rs2::depth_frame>(rs_frame)) {}

    const uint8_t* data() const { return (uint8_t*)rs_frame.get_data(); }
    const int rows() const { return std::max(rs_frame.get_height(), 0); }
    const int cols() const { return std::max(rs_frame.get_width(), 0); }
    const int bytes_per_pixel() const { return rs_frame.get_bytes_per_pixel(); }
    const float units() const { return rs_frame.get_units(); }
};

class PoseData {
   private:
    rs2_pose rs_pose;

   public:
    PoseData(rs2_pose rs_pose) : rs_pose(std::forward<rs2_pose>(rs_pose)) {}

    const uint mapper_confidence() { return rs_pose.mapper_confidence; }
    const uint tracker_confidence() { return rs_pose.tracker_confidence; }
    const rs2_quaternion rotation() { return rs_pose.rotation; }
    const rs2_vector acceleration() { return rs_pose.acceleration; }
    const rs2_vector angular_acceleration() { return rs_pose.angular_acceleration; }
    const rs2_vector angular_velocity() { return rs_pose.angular_velocity; }
    const rs2_vector translation() { return rs_pose.translation; }
    const rs2_vector velocity() { return rs_pose.velocity; }
};

class PoseFrame {
   public:
    rs2::pose_frame rs_frame;

    PoseFrame(rs2::pose_frame rs_frame) : rs_frame(std::forward<rs2::pose_frame>(rs_frame)) {}

    PoseData data() { return {rs_frame.get_pose_data()}; }
};

class Frame {
   public:
    rs2::frameset rs_frames;

    Frame(rs2::frameset rs_frames) : rs_frames(std::forward<rs2::frameset>(rs_frames)) {}

    VideoFrame rgb() const { return {rs_frames.get_color_frame()}; }
    DepthFrame depth() const { return {rs_frames.get_depth_frame()}; }
    PoseFrame pose() const { return {rs_frames.get_pose_frame()}; }
    unsigned long long frame_number() const { return rs_frames.get_frame_number(); }
    double timestamp() const { return rs_frames.get_timestamp(); }
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
        Frame* frame = new Frame(frames);
        return frame;
    }
};

void test() {
    rs2::pipeline pipe;
    pipe.start();

    // This is strangely slow. Probably need to take a closer look at this:
    // https://github.com/IntelRealSense/librealsense/wiki/Frame-Buffering-Management-in-RealSense-SDK-2.0

    // Gets the first frame.
    auto first_frame = pipe.wait_for_frames();
    auto start_timestamp = first_frame.get_timestamp();

    for (size_t i = 0; i < 1000; i++) {
        auto frame = pipe.wait_for_frames();
        auto timestamp = (frame.get_timestamp() - start_timestamp) / 1000.0;
        std::cout << "frame " << i << ": fps=" << (i + 1) / timestamp << ", size=" << frame.size() << "\n";
    }
    std::cout << "Done.\n";
}

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

    pybind11::class_<DepthFrame>(m, "DepthFrame", pybind11::buffer_protocol())
        .def_buffer([](DepthFrame& m) -> pybind11::buffer_info {
            auto buf = pybind11::buffer_info(m.data(), sizeof(uint8_t), true);
            buf.format = pybind11::format_descriptor<uint8_t>::format();
            buf.ndim = 3;
            buf.shape = {m.rows(), m.cols(), m.bytes_per_pixel()};
            buf.strides = {m.cols() * m.bytes_per_pixel(), m.bytes_per_pixel(), 1};
            return buf;
        })
        .def_property_readonly("rows", &DepthFrame::rows)
        .def_property_readonly("cols", &DepthFrame::cols)
        .def_property_readonly("bytes_per_pixel", &DepthFrame::bytes_per_pixel)
        .def_property_readonly("units", &DepthFrame::units);

    pybind11::class_<PoseData>(m, "PoseData")
        .def_property_readonly("mapper_confidence", &PoseData::mapper_confidence)
        .def_property_readonly("tracker_confidence", &PoseData::tracker_confidence)
        .def_property_readonly("rotation", &PoseData::rotation)
        .def_property_readonly("acceleration", &PoseData::acceleration)
        .def_property_readonly("angular_acceleration", &PoseData::angular_acceleration)
        .def_property_readonly("angular_velocity", &PoseData::angular_velocity)
        .def_property_readonly("translation", &PoseData::translation)
        .def_property_readonly("velocity", &PoseData::velocity);

    pybind11::class_<PoseFrame>(m, "PoseFrame").def_property_readonly("data", &PoseFrame::data);

    pybind11::class_<Frame>(m, "Frame")
        .def_property_readonly("rgb", &Frame::rgb)
        .def_property_readonly("depth", &Frame::depth)
        .def_property_readonly("pose", &Frame::pose)
        .def_property_readonly("frame_number", &Frame::frame_number)
        .def_property_readonly("timestamp", &Frame::timestamp);

    pybind11::class_<FrameGenerator>(m, "FrameGenerator")
        .def(pybind11::init<>())
        .def("__iter__", &FrameGenerator::iter)
        .def("__next__", &FrameGenerator::next);

    m.def("test", &test);
}

}  // namespace stretch::realsense
