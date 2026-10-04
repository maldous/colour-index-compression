#include "cix_spatial_bridge.h"

#include <charls/charls.h>
#include <charls/version.h>
#include <openjpeg.h>

#include <algorithm>
#include <cstring>
#include <limits>
#include <new>
#include <memory>
#include <vector>

namespace {
bool bytes(uint32_t w, uint32_t h, size_t* out) {
  if (!w || !h || size_t(w) > std::numeric_limits<size_t>::max() / size_t(h)) return false;
  size_t n=size_t(w)*size_t(h); if(n>std::numeric_limits<size_t>::max()/2) return false; *out=n*2; return true;
}
bool valid(uint32_t bits) { return bits>0 && bits<=16; }
bool jls_valid(uint32_t bits) { return bits>=2 && bits<=16; }
int copy_out(std::vector<uint8_t>& in, size_t max, cix_spatial_buffer* out) {
  if (in.empty() || in.size()>max) return CIX_SPATIAL_OUTPUT_LIMIT;
  uint8_t* p=new uint8_t[in.size()]; std::memcpy(p,in.data(),in.size()); out->data=p; out->size=in.size(); return CIX_SPATIAL_OK;
}
struct JlsEnc { charls_jpegls_encoder* p=charls_jpegls_encoder_create(); ~JlsEnc(){charls_jpegls_encoder_destroy(p);} };
struct JlsDec { charls_jpegls_decoder* p=charls_jpegls_decoder_create(); ~JlsDec(){charls_jpegls_decoder_destroy(p);} };
struct Mem { const uint8_t* in=nullptr; size_t in_size=0,pos=0,max=0; std::vector<uint8_t> out; bool failed=false; };
OPJ_SIZE_T read_mem(void* dst, OPJ_SIZE_T n, void* opaque) { auto* m=static_cast<Mem*>(opaque); size_t avail=m->in_size-m->pos; if(!avail)return static_cast<OPJ_SIZE_T>(-1); size_t take=std::min<size_t>(avail,n);std::memcpy(dst,m->in+m->pos,take);m->pos+=take;return take; }
OPJ_SIZE_T write_mem(void* src, OPJ_SIZE_T n, void* opaque) { auto* m=static_cast<Mem*>(opaque); try { if(n>m->max-m->out.size()){m->failed=true;return static_cast<OPJ_SIZE_T>(-1);} auto* b=static_cast<uint8_t*>(src);m->out.insert(m->out.end(),b,b+n);return n; } catch (...) {m->failed=true;return static_cast<OPJ_SIZE_T>(-1);} }
OPJ_OFF_T skip_mem(OPJ_OFF_T n, void* opaque) { auto* m=static_cast<Mem*>(opaque); if(n<0 || static_cast<uint64_t>(n)>m->in_size-m->pos)return -1;m->pos+=static_cast<size_t>(n);return n; }
OPJ_BOOL seek_mem(OPJ_OFF_T n, void* opaque) { auto* m=static_cast<Mem*>(opaque); if(n<0||static_cast<uint64_t>(n)>m->in_size)return OPJ_FALSE;m->pos=static_cast<size_t>(n);return OPJ_TRUE; }
opj_stream_t* stream_in(Mem* m) { auto* s=opj_stream_create(4096,OPJ_TRUE);if(!s)return nullptr;opj_stream_set_user_data(s,m,nullptr);opj_stream_set_user_data_length(s,m->in_size);opj_stream_set_read_function(s,read_mem);opj_stream_set_skip_function(s,skip_mem);opj_stream_set_seek_function(s,seek_mem);return s; }
opj_stream_t* stream_out(Mem* m) { auto* s=opj_stream_create(4096,OPJ_FALSE);if(!s)return nullptr;opj_stream_set_user_data(s,m,nullptr);opj_stream_set_write_function(s,write_mem);return s; }
bool jls_exact_end(const uint8_t* input, size_t size) {
  // JPEG-LS headers are marker/length segments until SOS. In entropy data,
  // bit stuffing makes FF followed by any byte below 0x80 data; restart
  // markers are also data for the purpose of locating the sole terminal EOI.
  if (size < 4 || input[0] != 0xff || input[1] != 0xd8) return false;
  size_t at = 2;
  while (at + 1 < size) {
    if (input[at] != 0xff) return false;
    const uint8_t marker = input[at + 1]; at += 2;
    if (marker == 0xda) { // SOS has a length-delimited header.
      if (at + 2 > size) return false;
      const size_t length = (size_t(input[at]) << 8) | input[at + 1];
      if (length < 2 || length - 2 > size - at - 2) return false;
      at += length;
      break;
    }
    if (marker == 0xd9) return at == size;
    if (at + 2 > size) return false;
    const size_t length = (size_t(input[at]) << 8) | input[at + 1];
    if (length < 2 || length - 2 > size - at - 2) return false;
    at += length;
  }
  while (at + 1 < size) {
    if (input[at++] != 0xff) continue;
    const uint8_t marker = input[at++];
    // JPEG-LS bit stuffing emits FF followed by any byte below 0x80.
    if (marker < 0x80 || (marker >= 0xd0 && marker <= 0xd7)) continue;
    return marker == 0xd9 && at == size;
  }
  return false;
}
bool exact_terminal_eoc(const uint8_t* input, size_t size) {
  // JPEG 2000 COM and other header marker payloads may contain FFD9. Parse
  // their declared lengths and Psot tile-part boundaries, then inspect only
  // packet data for EOC. MQ coding makes FF followed by 00..8F packet data.
  if (size < 4 || input[0] != 0xff || input[1] != 0x4f) return false;
  size_t at = 2, tile_end = 0; bool header = true;
  while (at + 1 < size) {
    if (header) {
      if (input[at] != 0xff) return false;
      const size_t marker_at = at;
      const uint8_t marker = input[at + 1]; at += 2;
      if (marker == 0xd9) return at == size;
      if (marker == 0x93) { header = false; continue; } // SOD
      if (at + 2 > size) return false;
      const size_t length = (size_t(input[at]) << 8) | input[at + 1];
      if (length < 2 || length - 2 > size - at - 2) return false;
      if (marker == 0x90) { // SOT: Psot bounds this tile-part's packet data.
        if (length != 10 || at + 10 > size) return false;
        const size_t psot = (size_t(input[at + 4]) << 24) |
                            (size_t(input[at + 5]) << 16) |
                            (size_t(input[at + 6]) << 8) | input[at + 7];
        if (psot && psot > size - marker_at) return false;
        tile_end = psot ? marker_at + psot : 0;
        if (tile_end && (tile_end < at + length || tile_end > size)) return false;
      }
      at += length;
    } else {
      if (tile_end && at == tile_end) { header = true; continue; }
      if (tile_end && at > tile_end) return false;
      if (input[at++] != 0xff) continue;
      const uint8_t marker = input[at++];
      // MQ bit stuffing makes FF followed by 00..8F packet data.
      if (marker <= 0x8f) continue;
      if (marker == 0x91) { // SOP is length-delimited inside packet data.
        if (at + 2 > size) return false;
        const size_t length = (size_t(input[at]) << 8) | input[at + 1];
        if (length != 4 || length - 2 > size - at - 2) return false;
        at += length; continue;
      }
      if (marker == 0x92) continue; // EPH
      if (marker == 0x90) { at -= 2; header = true; continue; } // next SOT
      return marker == 0xd9 && at == size;
    }
  }
  return false;
}
struct OpjCodec { opj_codec_t* p; explicit OpjCodec(bool encode):p(encode?opj_create_compress(OPJ_CODEC_J2K):opj_create_decompress(OPJ_CODEC_J2K)){} ~OpjCodec(){if(p)opj_destroy_codec(p);} };
int j2k_encode(const uint8_t* pixels,uint32_t w,uint32_t h,uint32_t bits,size_t max,cix_spatial_buffer* out) {
  opj_image_cmptparm_t component{}; component.dx=component.dy=1;component.w=w;component.h=h;component.prec=bits;component.sgnd=0;
  std::unique_ptr<opj_image_t, decltype(&opj_image_destroy)> image(opj_image_create(1,&component,OPJ_CLRSPC_GRAY),opj_image_destroy); if(!image)return CIX_SPATIAL_ALLOCATION_FAILURE;
  image->x1=w;image->y1=h; size_t count=size_t(w)*h; for(size_t i=0;i<count;++i)image->comps[0].data[i]=uint16_t(pixels[i*2])|(uint16_t(pixels[i*2+1])<<8);
  opj_cparameters_t params;opj_set_default_encoder_parameters(&params);params.tcp_numlayers=1;params.tcp_rates[0]=0;params.cp_disto_alloc=1;params.irreversible=0; uint32_t minimum=std::min(w,h), resolutions=1;while(minimum>1){minimum>>=1;++resolutions;}params.numresolution=std::min<int>(params.numresolution,resolutions);
  OpjCodec codec(true);Mem mem;mem.max=max;std::unique_ptr<opj_stream_t, decltype(&opj_stream_destroy)> stream(stream_out(&mem),opj_stream_destroy); bool ok=codec.p&&stream&&opj_setup_encoder(codec.p,&params,image.get())&&opj_start_compress(codec.p,image.get(),stream.get())&&opj_encode(codec.p,stream.get())&&opj_end_compress(codec.p,stream.get())&&!mem.failed; if(!ok)return CIX_SPATIAL_ENCODE_FAILURE;return copy_out(mem.out,max,out);
}
int j2k_decode(const uint8_t* input,size_t input_size,uint32_t w,uint32_t h,uint32_t bits,uint8_t* output,size_t output_size,bool only_probe,cix_spatial_info* info) {
  Mem mem;mem.in=input;mem.in_size=input_size;auto* stream=stream_in(&mem);OpjCodec codec(false);opj_dparameters_t params;opj_set_default_decoder_parameters(&params);opj_image_t* image=nullptr;bool ok=codec.p&&stream&&opj_setup_decoder(codec.p,&params)&&opj_read_header(stream,codec.p,&image);if(!ok){if(stream)opj_stream_destroy(stream);if(image)opj_image_destroy(image);return CIX_SPATIAL_DECODE_FAILURE;}
  bool shape=image->numcomps==1&&image->x0==0&&image->y0==0&&image->x1==w&&image->y1==h&&image->comps[0].w==w&&image->comps[0].h==h&&image->comps[0].dx==1&&image->comps[0].dy==1&&image->comps[0].prec==bits&&!image->comps[0].sgnd; if(!shape){opj_stream_destroy(stream);opj_image_destroy(image);return CIX_SPATIAL_UNSUPPORTED;} if(!exact_terminal_eoc(input,input_size)){opj_stream_destroy(stream);opj_image_destroy(image);return CIX_SPATIAL_DECODE_FAILURE;} if(info){info->width=w;info->height=h;info->bits_per_sample=bits;} if(only_probe){opj_stream_destroy(stream);opj_image_destroy(image);return CIX_SPATIAL_OK;}
  // `mem.pos` may read ahead. Require the one terminal EOC marker instead,
  // which rejects a valid codestream followed by bytes and a forged final EOC.
  ok=opj_decode(codec.p,stream,image)&&opj_end_decompress(codec.p,stream)&&exact_terminal_eoc(input,input_size); if(ok){for(size_t i=0;i<size_t(w)*h;++i){uint32_t v=image->comps[0].data[i];if(v>65535){ok=false;break;}output[i*2]=uint8_t(v);output[i*2+1]=uint8_t(v>>8);}}opj_stream_destroy(stream);opj_image_destroy(image);return ok?CIX_SPATIAL_OK:CIX_SPATIAL_DECODE_FAILURE;
}
int jls_info(const uint8_t* in,size_t size,uint32_t w,uint32_t h,uint32_t bits,charls_frame_info* frame) {
  if(!jls_exact_end(in,size)) return CIX_SPATIAL_DECODE_FAILURE;
  JlsDec d; if(!d.p || charls_jpegls_decoder_set_source_buffer(d.p,in,size)!=charls::jpegls_errc::success ||
    charls_jpegls_decoder_read_header(d.p)!=charls::jpegls_errc::success ||
    charls_jpegls_decoder_get_frame_info(d.p,frame)!=charls::jpegls_errc::success) return CIX_SPATIAL_DECODE_FAILURE;
  int32_t near=1;
  charls::interleave_mode interleave=charls::interleave_mode::line;
  if(frame->width!=w || frame->height!=h || frame->component_count!=1 || frame->bits_per_sample!=int32_t(bits) ||
    charls_jpegls_decoder_get_near_lossless(d.p,0,&near)!=charls::jpegls_errc::success || near!=0 ||
    charls_jpegls_decoder_get_interleave_mode(d.p,&interleave)!=charls::jpegls_errc::success || interleave!=charls::interleave_mode::none) return CIX_SPATIAL_UNSUPPORTED;
  return CIX_SPATIAL_OK;
}
}

extern "C" int cix_spatial_encode_u16_gray(uint32_t codec,const uint8_t* pixels,size_t size,uint32_t w,uint32_t h,uint32_t bits,size_t max,cix_spatial_buffer* out) {
  if(!out) return CIX_SPATIAL_INVALID_ARGUMENT; out->data=nullptr;out->size=0;
  size_t required=0; if(!pixels || !max || !valid(bits) || !bytes(w,h,&required) || size!=required) return CIX_SPATIAL_INVALID_ARGUMENT;
  try {
    if(codec==CIX_SPATIAL_JPEG2000) return j2k_encode(pixels,w,h,bits,max,out);
    if(codec!=CIX_SPATIAL_JPEGLS) return CIX_SPATIAL_UNSUPPORTED;
    if(!jls_valid(bits)) return CIX_SPATIAL_UNSUPPORTED;
    JlsEnc enc; if(!enc.p) return CIX_SPATIAL_ALLOCATION_FAILURE;
    // CharLS consumes canonical u16 LE pixels. Keep significant precision in
    // the frame so 8-bit samples retain their historical numeric values.
    charls_frame_info frame{w,h,static_cast<int32_t>(bits),1};
    size_t estimate=0;
    if(charls_jpegls_encoder_set_frame_info(enc.p,&frame)!=charls::jpegls_errc::success ||
      charls_jpegls_encoder_set_near_lossless(enc.p,0)!=charls::jpegls_errc::success ||
      charls_jpegls_encoder_set_interleave_mode(enc.p,charls::interleave_mode::none)!=charls::jpegls_errc::success ||
      charls_jpegls_encoder_get_estimated_destination_size(enc.p,&estimate)!=charls::jpegls_errc::success || estimate==0 || estimate>max) return CIX_SPATIAL_ENCODE_FAILURE;
    std::vector<uint8_t> encoded(estimate);
    std::vector<uint8_t> packed;
    const uint8_t* source=pixels;
    size_t source_size=size;
    uint32_t stride=w*2;
    if(bits<=8) {
      packed.reserve(size/2);
      for(size_t at=0;at<size;at+=2) packed.push_back(pixels[at]);
      source=packed.data(); source_size=packed.size(); stride=w;
    }
    if(charls_jpegls_encoder_set_destination_buffer(enc.p,encoded.data(),encoded.size())!=charls::jpegls_errc::success ||
      charls_jpegls_encoder_encode_from_buffer(enc.p,source,source_size,stride)!=charls::jpegls_errc::success) return CIX_SPATIAL_ENCODE_FAILURE;
    size_t written=0; if(charls_jpegls_encoder_get_bytes_written(enc.p,&written)!=charls::jpegls_errc::success || !written || written>encoded.size()) return CIX_SPATIAL_ENCODE_FAILURE;
    encoded.resize(written); return copy_out(encoded,max,out);
  } catch(const std::bad_alloc&) { return CIX_SPATIAL_ALLOCATION_FAILURE; } catch(...) { return CIX_SPATIAL_EXCEPTION; }
}

extern "C" int cix_spatial_probe_gray(uint32_t codec,const uint8_t* input,size_t input_size,uint32_t w,uint32_t h,uint32_t bits,cix_spatial_info* out) {
  if(!input || !input_size || !out || !valid(bits)) return CIX_SPATIAL_INVALID_ARGUMENT;
  std::memset(out,0,sizeof(*out));
  try { if(codec==CIX_SPATIAL_JPEG2000) return j2k_decode(input,input_size,w,h,bits,nullptr,0,true,out); if(codec!=CIX_SPATIAL_JPEGLS || !jls_valid(bits)) return CIX_SPATIAL_UNSUPPORTED; charls_frame_info frame{}; int status=jls_info(input,input_size,w,h,bits,&frame); if(status!=CIX_SPATIAL_OK) return status; out->width=w;out->height=h;out->bits_per_sample=bits;return CIX_SPATIAL_OK; }
  catch(const std::bad_alloc&) { return CIX_SPATIAL_ALLOCATION_FAILURE; } catch(...) { return CIX_SPATIAL_EXCEPTION; }
}

extern "C" int cix_spatial_decode_u16_gray(uint32_t codec,const uint8_t* input,size_t input_size,uint32_t w,uint32_t h,uint32_t bits,uint8_t* output,size_t output_size) {
  size_t required=0; if(!input||!input_size||!output||!valid(bits)||!bytes(w,h,&required)||output_size!=required) return CIX_SPATIAL_INVALID_ARGUMENT;
  try { if(codec==CIX_SPATIAL_JPEG2000) return j2k_decode(input,input_size,w,h,bits,output,output_size,false,nullptr); if(codec!=CIX_SPATIAL_JPEGLS || !jls_valid(bits)) return CIX_SPATIAL_UNSUPPORTED; if(!jls_exact_end(input,input_size)) return CIX_SPATIAL_DECODE_FAILURE; JlsDec d; charls_frame_info frame{}; if(!d.p || charls_jpegls_decoder_set_source_buffer(d.p,input,input_size)!=charls::jpegls_errc::success || charls_jpegls_decoder_read_header(d.p)!=charls::jpegls_errc::success || charls_jpegls_decoder_get_frame_info(d.p,&frame)!=charls::jpegls_errc::success || frame.width!=w||frame.height!=h||frame.component_count!=1||frame.bits_per_sample!=int32_t(bits)) return CIX_SPATIAL_UNSUPPORTED; size_t destination=0; const size_t packed_size=bits<=8?required/2:required; const uint32_t stride=bits<=8?w:w*2; if(charls_jpegls_decoder_get_destination_size(d.p,stride,&destination)!=charls::jpegls_errc::success || destination!=packed_size) return CIX_SPATIAL_DECODE_FAILURE; if(bits<=8){std::vector<uint8_t> packed(packed_size);if(charls_jpegls_decoder_decode_to_buffer(d.p,packed.data(),packed.size(),stride)!=charls::jpegls_errc::success)return CIX_SPATIAL_DECODE_FAILURE;for(size_t at=0;at<packed.size();++at){output[at*2]=packed[at];output[at*2+1]=0;}} else if(charls_jpegls_decoder_decode_to_buffer(d.p,output,output_size,stride)!=charls::jpegls_errc::success) return CIX_SPATIAL_DECODE_FAILURE; return CIX_SPATIAL_OK; }
  catch(const std::bad_alloc&) { return CIX_SPATIAL_ALLOCATION_FAILURE; } catch(...) { return CIX_SPATIAL_EXCEPTION; }
}
extern "C" void cix_spatial_free_buffer(cix_spatial_buffer* b){if(!b)return;delete[] b->data;b->data=nullptr;b->size=0;}
extern "C" uint32_t cix_spatial_charls_version(void){int32_t a=0,b=0,c=0;charls_get_version_number(&a,&b,&c);return uint32_t(a*10000+b*100+c);}
extern "C" uint32_t cix_spatial_openjpeg_version(void){return (OPJ_VERSION_MAJOR*10000)+(OPJ_VERSION_MINOR*100)+OPJ_VERSION_BUILD;}
extern "C" const char* cix_spatial_bridge_version(void){return "cix-spatial-charls-openjpeg/1";}
