use Compress::Raw::Zlib;
sub v{my$x=shift;my$s='';while($x>=128){$s.=pack('C',($x&127)|128);$x>>=7}$s.=pack('C',$x);$s}
my($mode,$input,$payload)=@ARGV;open my$i,'<',$input;local$/;my$in=<$i>;open my$p,'<',$payload;my$body=<$p>;print 'CIXM6',v(1048576),pack('C',$mode),v(length$in),v(length$body),$body,pack('C',255),v(length$in),pack('V',crc32($in));
